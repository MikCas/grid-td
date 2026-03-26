TDF = op.TDModules.mod.TDFunctions # utility functions
from TDStoreTools import StorageManager
import math

class CameraExt():
	"""
	The CameraExt Class helps with interactively controlling a Camera COMP
	given a Container COMP with the Mouse UV Buttons Parameters for left, 
	middle and right enabled.

	Attributes
	----------
		ownerComp : OP
			Reference to the COMP this Class is initiated by.
			
		CameraTransform : tdu.Matrix
			Get or set the camera transformation matrix .
			
		Camera : tdu.Camera
			Get or set the underlying camera object.
			
		Pivot : tdu.Vector
			3D vector where the camera moves around
		PivotUV : tdu.vector
			The 2D screenspace position of the pivot
			
		TransformActive : boolean
			True between a StartTransform and EndTransform call.

	Methods
	-------
		StartTransform(action=None, u=0, v=0, mode)
			Begins a transform by setting the action, updating the pivot and setting the speed.
		Transform(u=0, v=0, du=None, dv=None, scaler=1)
			Applies a transform to the camera based on the given movement and the action/mode/speed set in StartTransform
		EndTransform()
			Called at the end of the transform to reset the state.

		AutoRotate(time)
			Performs an autotumble action for the given amount of time in seconds
		Move3D(translate, rotate)
			Apply a 3D movement using the given 3 dimensional translation and rotation vectors
		OrthoZoom(dx)
			Perform an orthographic zoom.
		Blend(targetCamera, blendFactor)
			Returns a tdu.Camera object that is a blend between this camera and the given target using the given 0-1 blend factor.
			The returned camera can be used to initialize the camera member of another cameraViewport COMP.
		
		ResetKeys()
			Reset the status of pressed keys
		SetKeyAction(action, newActive)
			Set whether a key is pressed or not.
		DoKeyMovement(time)
			Execute the actions for any pressed keys for the given amount of time.
			
		Reset()
			Resets the camera.
		SetHome(newHome)
			Set the home transform matrix.
		SetHomeToCurrent()
			Set the home transform to the current camera transform.
		ResetHome()
			Set the home transform to the default position.
		Home()
			Set the camera to the home position.
		Frame()
			Move the camera so that all objects are within the camera bounds but the orientation remains the same.
		FrameLookAt(dir, up)
			Set the orientation of the camera and then set the position so that all objects are within the camera frame.
		Top(), Front(), Right(), Left(), Back(), Bottom()
			Frame the camera looking at given angle of the scene.
		SetPosAndAngle(pos, angle)
			Sets the camera orientation using a 3D position and a 3D rotation.
			
		OpenViewMenu()
			Open the view menu.

	"""
	
	def __init__(self, ownerComp : OP):
		#The component to which this extension is attached
		self.ownerComp = ownerComp
		self.cameraInst = tdu.Camera()
		
		# for tracking the change in mouse movement
		self.lastU = 0
		self.lastV = 0
		self.startTime = 0
		
		# for the auto rotate
		self.spinMoves = []				
		self.spinSpeed = (0.0, 0.0)			
		self.spinStartMatrix = tdu.Matrix()
		self.spinTime = 0
		self.spinStoping = False
		self.spinStopLife = 0
		self.lastdU = 0
		self.lastdV = 0

		self.didCameraMove = False
		
		self.camSpeed = (1.0, 1.0)
		
		self.keyStates = {}
		
		# navigation mode and current action
		self.mode = "viewport"
		self.action = ""
		
		self._cameraTransform = tdu.Dependency(0)

		# if we've defined an external dat to save, pull the transform from there
		# this allows us to clone immune the data
		if parent.Camera.par.Transformdat:
			self.CameraTransform = tdu.Matrix( parent.Camera.par.Transformdat.eval() )
		else:
			self.CameraTransform = ownerComp.fetch('CameraTransform', tdu.Matrix( [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 5, 1] ) )

		self.sequenceStartMatrix = tdu.Matrix(self.CameraTransform)
		self.sequenceStartBlend = parent.Camera.par.Sequence.eval()
		self.lastSequenceBlend = self.sequenceStartBlend
		self.lastSequenceBlendChange = None

		self._pivotDistance = tdu.Dependency(0)
		
		TDF.createProperty(self, 'PivotActive', value=False, readOnly=True)
		TDF.createProperty(self, 'TransformActive', value=False, readOnly=True)
		TDF.createProperty(self, 'presetIndex', value=0, readOnly=False)
		
		# stored items (persistent across saves and re-initialization):
		storedItems = [
			{'name': 'Pivot', 'default': tdu.Vector(0,0,0) },
			{'name': 'PivotUV', 'default': (0,0) },
			{'name': 'presetIndex', 'default': 0 }
		]

		self.stored = StorageManager(self, ownerComp, storedItems)

		self.cameraInst.pivot = self.Pivot

	@property
	def CameraTransform(self):
		return self._cameraTransform.val

	@CameraTransform.setter
	def CameraTransform(self, val):
		self._cameraTransform.val = val
		self.cameraInst.setTransform( self._cameraTransform.val )
		self.ownerComp.store('CameraTransform', val)
		
		if parent.Camera.par.Transformdat:
			val.fillTable( parent.Camera.par.Transformdat.eval() )
		
	@property
	def Camera(self):
		return self.cameraInst

	@Camera.setter
	def Camera(self, val):
		self.cameraInst = val
		self._cameraTransform.val = self.cameraInst.transform()
		
	@property
	def PivotDistance(self):
		self._pivotDistance.val = (self.cameraInst.position - self.cameraInst.pivot).length()
		return self._pivotDistance.val

	@PivotDistance.setter
	def PivotDistance(self, val):
		
		if self.mode == "object":
			self.cameraInst.pivot = self.getPivotFromObjects()
		
		#dir = self.cameraInst.dir
		dir = self.cameraInst.pivot - self.cameraInst.position
		dir.normalize()
		
		self.cameraInst.position = self.cameraInst.pivot - (dir * val)
		self._pivotDistance.val = val
		
		self.fillMat()

	def getAspect(self):
	
		if parent.Camera.par.Refpanel.eval() == None:
			return 1
	
		aspect = op(parent.Camera.par.Refpanel).width / op(parent.Camera.par.Refpanel).height
		
		return aspect
		
	def getHfov(self):
	
		aspect = self.getAspect()
		fov = parent.Camera.par.fov / 180 * math.pi
		
		if parent.Camera.par.viewanglemethod == 'horzfov':
			return fov
			
		elif parent.Camera.par.viewanglemethod == 'vertfov':
			return fov * aspect
		
		# todo: handle focal length/aperature
		return 45

	# calculate a common speed mult based on the pivot distance, fov and panel aspect
	def calcCameraSpeed(self):
	
		if parent.Camera.par.Orthographic:
			return parent.Camera.par.orthowidth, parent.Camera.par.orthowidth / self.getAspect()
		
		else:
		
			pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length()
			
			pivotWidth = pivotDist
			pivotHeight = pivotDist
			
			aspect = self.getAspect()
			
			if parent.Camera.par.viewanglemethod == 'horzfov':
				pivotWidth = 2.0 * pivotDist * math.tan( parent.Camera.par.fov / 2 / 180 * math.pi )
				pivotHeight = pivotWidth / aspect
					
			elif parent.Camera.par.viewanglemethod == 'vertfov':
				pivotHeight = 2.0 * pivotDist * math.tan( parent.Camera.par.fov / 2 / 180 * math.pi )
				pivotWidth = pivotHeight * aspect
				
			# todo: we don't handle the focal length / aperature model right now
			
			speedu = pivotWidth
			speedv = pivotHeight
	
			return speedu, speedv
		
	# return the current coords in the render pick chop
	def getPickPos(self, u, v):
	
		pickNode = op('renderpick1')
		pickEvent = pickNode.pick(u, v)
		if pickEvent.pickOp is not None:
			return pickEvent.pos
	
		return None

	# set the pivot to the center of the viewport at the same distance as the last pivot
	def getPivotFromViewportCenter(self):
	
		pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length()
		pivotDist = max(pivotDist, 0.1)
		
		pivotPos = tdu.Position(0, 0, -1 * pivotDist)
		pivotPos = self.CameraTransform * pivotPos
		
		return pivotPos

	# set the pivot to a ray going through the given u,v position at the same distance as the last pivot
	def getPivotFromCursor(self, u, v):
	
		pivotDist = (self.cameraInst.position - self.cameraInst.pivot).length()
		pivotDist = max(pivotDist, 0.1)

		screenPos = tdu.Position( (u * 2) -1, (v * 2) - 1, 0 )

		projMat = me.parent().projectionInverse( self.getAspect(), 1 )
		viewProjMat = self.CameraTransform * projMat
		
		worldPos1 = viewProjMat * screenPos
		
		screenPos.z = 1.0
		worldPos2 = viewProjMat * screenPos
		
		camDir = worldPos2 - worldPos1
		camDir.normalize()

		camPos = tdu.Vector( self.CameraTransform.vals[12], self.CameraTransform.vals[13], self.CameraTransform.vals[14] )
		
		pivotPos = camPos + (camDir * pivotDist)
		return pivotPos
		
	# loop through all geos given in the rendertop's geometry list and find the max bounds	
	def getObjectBounds(self):
	
		bmin = None
		bmax = None
	
		if parent.Camera.par.Boundsmode.eval() == "manual":
			
			bmin = parent.Camera.parGroup.Minbounds.eval()
			bmax = parent.Camera.parGroup.Maxbounds.eval()
	
		else:
			
			renderOp = parent.Camera.par.Refrender.eval()
			if renderOp is None:
				return tdu.Vector(0), tdu.Vector(0)
					
			geoOps = renderOp.parent().ops( renderOp.par.geometry.val )
		
			for gop in geoOps:
			
				if getattr(gop, 'computeBounds', None) is not None:
					
					if not ('cameraViewportExcludeBounds' in gop.tags):
				
						# we only care about the render flag/parameter
						bounds = gop.computeBounds(display=False, render=True, selected=False, recurse=True)
						
						# only set if we get a valid bounds back from the 
						if bounds.size != tdu.Position(0) or bounds.center != tdu.Position(0):
							
							if bmin is None:
								bmin = bounds.min
							
							if bmax is None:
								bmax = bounds.max	
								
							for i in range(3):
								bmin[i] = min(bmin[i], bounds.min[i])
								bmax[i] = max(bmax[i], bounds.max[i])
							
	
		if bmin is None:
			bmin = tdu.Vector(0)
			bmax = tdu.Vector(0)
	
		return bmin, bmax
	
	# set the pivot to the center of the selected bounding boxes
	def getPivotFromObjects(self):
	
		bmin, bmax = self.getObjectBounds()
	
		#geoComp = op( parent.Camera.par.Refgeo )
		if bmin is None:
			return tdu.Vector(0,0,0)
			
		#bounds = geoComp.computeBounds(display=True, render=True, selected=False, recurse=True)
	
		#print(bounds)
		#pivotPos = bounds[2]
		pivotPos = ( (bmin[0] + bmax[0]) / 2.0, (bmin[1] + bmax[1]) / 2.0, (bmin[2] + bmax[2]) / 2.0 )
	
		return pivotPos

	def GetAction(self):
		return self.action

	def StartTransform(self, action : str = None, u : float = 0, v : float = 0, mode = "cursor") -> None:

		self.lastU = float(u)
		self.lastV = float(v)
		self.startTime = absTime.seconds
		self.spinMoves = []

		self.mode = mode
		self.action = action
		
		# make sure this is false at the start of the transform
		self.didCameraMove = False
		
		# at the beginning of an auto-tumble, reset the camera to the initial start position
		if self.action == "autotumble":
			self.CameraTransform = self.spinStartMatrix
					
		# if we're not auto-tumbling, then reset
		else:
			self.spinTime = 0
			self.spinSpeed = (0.0, 0.0)
			self.lastdU = 0
			self.lastdV = 0

		
		if action is None:
			return
		
		newPivot = None
		
		if self.action == "3d":
			newPivot = self.getPivotFromObjects()
			
		elif self.ownerComp.par.Orthographic:
			newPivot = None
		
		# in cursor mode, we always try to get a new pivot
		elif mode == "cursor":
		
			pickPos = self.getPickPos(u, v)
			if not (pickPos is None):
				newPivot = pickPos
			
			else:
				newPivot = self.getPivotFromCursor(u, v)

		# if we're doing the tumble action
		elif self.action == "tumble" :
						
			if mode == "object":
				newPivot = self.getPivotFromObjects()
				
		# if we're doing a dolly (either by dragging or the mouse wheel)
		elif self.action == "dolly" or self.action == "wheel":
			newPivot = self.getPivotFromCursor(u, v)
			
		# don't change the pivot while auto-tumbling
		elif self.action == "autotumble":
			newPivot = self.cameraInst.pivot
		
			
		# if nothing else set the pivot, default to the center of the screen
		if newPivot is None:
			newPivot = self.getPivotFromViewportCenter()
	
		self.cameraInst.pivot = newPivot
		#self.PivotActive = True

		self.updatePivot()		
		self.camSpeed = self.calcCameraSpeed()
		self._TransformActive.val = True

		return

		
	def Transform(self, u : float = 0, v : float = 0, du : float = None, dv : float = None, scaler : float = 1) -> None:

		# if we're given du/dv use those (like from the mouse wheel), otherwise subtract from our last position
		deltaU = (u - self.lastU) if du is None else du
		deltaV = (v - self.lastV) if dv is None else dv
		
		# multiply by the camera speed and any user scaling
		moveU = deltaU * scaler
		moveV = deltaV * scaler
		
		# tumble/look
		if self.action == "tumble" or self.action == "autotumble":
		
			if self.mode == 'camera':
				self.cameraInst.look(moveU, moveV)
			else:
				self.cameraInst.tumble(moveU, moveV)

		# pan/track		
		elif self.action == "pan":
		
			if self.ownerComp.par.Orthographic:
				self.cameraInst.pan(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
			elif self.mode == 'camera':
				self.cameraInst.track(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
			else:
				self.cameraInst.pan(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
		
		# dolly/zoom
		elif self.action == "dolly":
			
			# we need to update the cam speed based on our new dist to the pivot
			self.camSpeed = self.calcCameraSpeed()
		
			if self.ownerComp.par.Orthographic:
				self.cameraInst.pan(moveU * self.camSpeed[0], moveV * self.camSpeed[1])
			elif self.mode == 'camera':
				self.cameraInst.walk( moveU, moveV * self.camSpeed[1] )
			else:
				self.cameraInst.dolly( (moveU * self.camSpeed[0]) + (moveV * self.camSpeed[1]) )
		
		# orthographic zoom
		elif self.action == "orthozoom":
			self.OrthoZoom( moveU + moveV )
				
		# wheel
		elif self.action == "wheel":
			self.cameraInst.dolly( (moveU * self.camSpeed[0]) + (moveV * self.camSpeed[1]) )
			
		# track the amount of movement each frame, we'll sample a window of this at the 
		# end to calculate our auto-rotate speed
		self.spinMoves.append( (absTime.seconds, moveU, moveV) )

		# flag that the camera was moved a little
		if abs(deltaU) > 0.001 or abs(deltaV) > 0.001:
			self.didCameraMove = True

		#self.PivotActive = True
		
		self.fillMat()
		self.lastU = float(u)
		self.lastV = float(v)
		self.updatePivot()

		return
		
	# just clear the current action when the mouse is released
	def EndTransform(self) -> bool:
	
		if self.action == "tumble" and parent().par.Autorotate:
			
			su = 0
			sv = 0
			curTime = absTime.seconds
			maxTime = 0.2
			
			# use a window filter to check just a sample of the mouse movement
			for m in self.spinMoves:
				if curTime - m[0] > 0.05 and curTime - m[0] < 0.25:
					su += m[1]
					sv += m[2]
					maxTime = max(maxTime, curTime - m[0])

			# rotate on whatever axis had the most movement
			if abs(su) > abs(sv):
				self.spinSpeed = ( su / maxTime, 0 )
			else:
				self.spinSpeed = ( 0, sv / maxTime )
		
		if self.action != "autotumble":
			self.spinStartMatrix = self.CameraTransform
			self.sequenceStartMatrix = self.CameraTransform
			self.sequenceStartBlend = parent().par.Sequence.eval()

		#self.PivotActive = False
		
		self.action = None
		self._TransformActive.val = False
		
		cameraMoved = self.didCameraMove
		self.didCameraMove = False
		
		return cameraMoved
		
	def AutoRotate(self, time) -> None:

		if self.spinStoping: 
			if self.spinStopLife == 0:
				self.spinStoping = False
				self.spinSpeed = (0, 0)
				self.spinTime = 0
			else:
				spinSpeedUDec = self.spinSpeed[0] * 1/self.spinStopLife
				spinSpeedVDec = self.spinSpeed[1] * 1/self.spinStopLife
				self.spinSpeed = (self.spinSpeed[0] - spinSpeedUDec, self.spinSpeed[1] - spinSpeedVDec)
				self.spinStopLife -= 1
	
		if (self.spinSpeed[0] != 0) or (self.spinSpeed[1] != 0):
		
			self.spinTime += time
		
			self.StartTransform(action="autotumble", u=0, v=0, mode=self.mode)

			self.lastdU = self.lastdU + (self.spinSpeed[0] * 1/me.time.rate)
			self.lastdV = self.lastdV + (self.spinSpeed[1] * 1/me.time.rate)

			self.Transform( du=self.lastdU, dv=self.lastdV, scaler=1)
	
			self.EndTransform()

	def StopAutoRotate(self) -> None:
	
		self.spinStopLife = round(self.ownerComp.par.Stoptime.eval() * me.time.rate, 0)
		self.spinStoping = True
		
		return

	# do a 3d move from a spacemouse via the joystick chop			
	def Move3D(self, translate, rotate) -> None:
	
		self.cameraInst.move3D( translate, rotate, mode="object" )
		
		self.fillMat()
		self.updatePivot()
	
		return
		
	def ResetKeys(self) -> None:
	
		self.keyStates = {}
	
		return
		
	def SetKeyAction(self, action, newActive) -> None:
	
		if not (action in self.keyStates.keys()):	
			self.keyStates[action] = { "active" : newActive }
		
		else:
			self.keyStates[action]["active"] = newActive
			
		return
	
	def DoKeyMovement(self, time) -> None:
	
		moved = False
		turnSpeed = self.ownerComp.par.Turnmult * time
		walkSpeed = self.ownerComp.par.Walkmult * time
	
		for action, state in self.keyStates.items():
		
			if state["active"]:
			
				if action == "track_left":
					self.cameraInst.track(-walkSpeed, 0)
				
				elif action == "track_right":
					self.cameraInst.track(walkSpeed, 0)
				
				elif action == "walk_forward":
					self.cameraInst.walk(0, walkSpeed)
				
				elif action == "walk_back":
					self.cameraInst.walk(0, -walkSpeed)
				
				elif action == "turn_left":
					self.cameraInst.walk(-turnSpeed, 0)
				
				elif action == "turn_right":
					self.cameraInst.walk(turnSpeed, 0)				
		
				
				moved = True
				
		
		if moved:
			self.fillMat()		 
		
		return
		
	def Reset(self) -> None:
	
		mat = tdu.Matrix()
		mat.translate(0,0,5)
		self.cameraInst.setTransform(mat)
		self.fillMat()
	
		self.cameraInst.pivot = tdu.Vector(0,0,0)
		self.updatePivot()
		
		return
		
	def SetHomeToCurrent(self) -> None:
		s, r, t = self.HomeTransform = self.cameraInst.transform().decompose()
		self.ownerComp.parGroup.Homeangle = r
		#self.fillHomeAngle()
		return
		
	def ResetHome(self) -> None:
		#self.HomeTransform = tdu.Matrix( [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 5, 1] ) 
		#self.fillHomeAngle()
		self.ownerComp.parGroup.Homeangle = (0,0,0)
		return
		
	def Home(self, selected : bool = False) -> None:
	
		# reset the cam to the default direction and then frame
		#self.Reset()
		#self.Frame(selected)
		#self.Front()
		
		home = tdu.Matrix()
		home.translate(0,0,5)
		home.rotate( self.ownerComp.par.Homeanglex, self.ownerComp.par.Homeangley, self.ownerComp.par.Homeanglez )
		
		self.cameraInst.setTransform( home )
		self.Frame()
	
		return

		
	def Frame(self, selected : bool = False) -> None:
	
		bmin, bmax = self.getObjectBounds()

		# if nothing was selected, do a full frame instead
		#if selected and tdu.Vector(bmin).length() == 0 and tdu.Vector(bmax).length() == 0:
		#	bounds = geoComp.computeBounds(display=True, render=True, selected=False, recurse=True)
				
		aspect = self.getAspect()
		hfov = self.getHfov()

		frameWidth = self.cameraInst.frameBounds( bmin, bmax, hfov, aspect, padding=parent.Camera.par.Padding )
		parent.Camera.par.orthowidth = frameWidth
				
		self.fillMat()
	
		return
		
	def FrameLookAt(self, dir, up : tdu.Vector(0,1,0) ) -> None:
	
		m = tdu.Matrix()
		center = tdu.Position(0,0,0)
		target = center + dir

		m.lookat( center, target, up )

		self.cameraInst.setTransform(m)
				
		self.Frame()
	
		return
		
	def SetPosAndAngle(self, pos, angle):
	
		mat = tdu.Matrix()
		mat.rotate( angle[0], angle[1], angle[2] )
		mat.translate( pos[0], pos[1], pos[2] )
		
		self.CameraTransform = mat
	
		return
		
	def Top(self):
		parent.Camera.FrameLookAt( tdu.Vector(0,-1,0), tdu.Vector(0,0,-1) )
		return
		
	def Front(self):
		parent.Camera.FrameLookAt( tdu.Vector(0,0,-1), tdu.Vector(0,1,0) )
		return
		
	def Right(self):
		parent.Camera.FrameLookAt( tdu.Vector(-1,0,0), tdu.Vector(0,1,0) )
		return
		
	def Left(self):
		parent.Camera.FrameLookAt( tdu.Vector(1,0,0), tdu.Vector(0,1,0) )
		return
		
	def Back(self):
		parent.Camera.FrameLookAt( tdu.Vector(0,0,1), tdu.Vector(0,1,0) )
		return
		
	def Bottom(self):
		parent.Camera.FrameLookAt( tdu.Vector(0,1,0), tdu.Vector(0,0,1) )
		return
		
	def OrthoZoom(self, dx):
	
		orthoWidth = parent.Camera.par.orthowidth
		
		dx = dx * parent.Camera.par.Dollymult
	
		if dx < 0:
			dx = 1 / (1 - dx)
		else:
			dx = 1 + dx
	
		orthoWidth /= dx
		
		parent.Camera.par.orthowidth = orthoWidth
			
		return
	
	def fillMat(self):
		# call the setter, which saves the current state to storage
		self.CameraTransform = self.cameraInst.transform()
		#self._cameraTransform.val = self.cameraInst.transform()
		parent.Camera.par.pxform = True
		return

	# update the home angle parameters based on the matrix in home mat		
	def fillHomeAngle(self):
		
		s, r, t = self.HomeTransform.decompose()
		
		self.ownerComp.par.Homeanglex = r[0]
		self.ownerComp.par.Homeangley = r[1]
		self.ownerComp.par.Homeanglez = r[2]
	
		return
	
	# return the current pivot position in 0-1 UV space	
	def updatePivot(self):
	
		self.Pivot = self.cameraInst.pivot
		
		pivot = tdu.Position( self.Pivot )
		
		projMat = me.parent().projection( self.getAspect(), 1 )
		invViewMat = tdu.Matrix(self.CameraTransform)
		invViewMat.invert()
		
		viewProjMat = projMat * invViewMat

		#print(pivot)
		#print(viewProjMat)
		pivot *= viewProjMat

		self.PivotUV = ( (pivot.x / pivot.z) * 0.5 + 0.5, (pivot.y / pivot.z) * 0.5 + 0.5 )

		return
		
	def BlendCamera(self, targetCamera, blend):
	
		blendCam = self.cameraInst.blendCamera( targetCamera.Camera, blend )
		
		return blendCam
	
	def getPresetMatrix(self, index):
		
		numPresets = self.ownerComp.seq['Preset'].numBlocks
		index = max(0, min(numPresets - 1, int(index)))
		
		pos = self.ownerComp.seq['Preset'][index].parGroup.Pos
		angle = self.ownerComp.seq['Preset'][index].parGroup.Angle
		mat = tdu.Matrix()
		mat.rotate( angle[0], angle[1], angle[2] )
		mat.translate( pos[0], pos[1], pos[2] )
		
		return mat
	
	# blend between 2 camera positions disregarding the auto-tumble offsets
	def BlendSequence(self, blend):
		
		numPresets = self.ownerComp.seq['Preset'].numBlocks
		maxPreset = numPresets - 1
		
		# is it spinnning?
		s = tdu.Vector(self.spinSpeed[0], self.spinSpeed[1], 0)
		spinning = False
		if s.length() > 0:
			spinning = True
			
		# check whether we've changed blend direction since the last call
		dirChange = False
		blendChange = blend - self.lastSequenceBlend
		if self.lastSequenceBlendChange and ((blendChange > 0) != (self.lastSequenceBlendChange > 0)):
			#print("dirChange")
			dirChange = True;
		
		self.lastSequenceBlend = blend
		self.lastSequenceBlendChange = blendChange
			
		#print(blend, self.sequenceStartBlend)
		
		# 0-1 between base and target
		blendValue = 0
		targetMat = None;
		baseMat = None;
		
		# below the first preset
		if blend < 0:
			self.sequenceStartBlend = blend
			self.sequenceStartMatrix = self.CameraTransform
			return
			
		# above the last preset
		elif blend >= maxPreset:
			
			if self.sequenceStartBlend < maxPreset or (blend <= maxPreset):
				self.sequenceStartBlend = maxPreset
				self.sequenceStartMatrix = self.getPresetMatrix( maxPreset )
			
			elif blend > self.sequenceStartBlend:
				self.sequenceStartBlend = blend
				self.sequenceStartMatrix = self.CameraTransform
			
			baseMat = self.sequenceStartMatrix
			targetMat = self.getPresetMatrix( maxPreset )
			
			if maxPreset == self.sequenceStartBlend:
				blendValue = 0
			else:
				blendValue = (blend - self.sequenceStartBlend) / (maxPreset - self.sequenceStartBlend)
			
			#print("above sequence: ", self.sequenceStartBlend, blendValue)
		
		# inside the sequence	
		else:

			# if we're exactly on a preset, go there
			if (math.modf(blend)[0] <= 0):
				self.sequenceStartBlend = blend
				self.sequenceStartMatrix = self.getPresetMatrix( self.sequenceStartBlend )
			
			# if we were outside of the given range (inclusive of both ends), then we jump to the interpolated pos
			elif (blend - math.floor(self.sequenceStartBlend) > 1) or (math.ceil(blend) < self.sequenceStartBlend):
				self.sequenceStartBlend = math.floor( blend )
				self.sequenceStartMatrix = self.getPresetMatrix( self.sequenceStartBlend )

			# if we're inside the range and changed direction, then reset the start matrix otherwise continue the blend 
			elif dirChange:
				self.sequenceStartBlend = blend
				self.sequenceStartMatrix = self.CameraTransform


			if blend >= self.sequenceStartBlend:
				targetIndex = math.ceil(blend)
				
			else:
				targetIndex = math.floor(blend)
									
			if targetIndex == self.sequenceStartBlend:
				blendVlaue = 0
			else:
				blendValue = (blend - self.sequenceStartBlend) / (targetIndex - self.sequenceStartBlend)
			
			baseMat = self.sequenceStartMatrix
			targetMat = self.getPresetMatrix( targetIndex )
			
			#print("mid sequence: ", self.sequenceStartBlend, targetIndex, blendValue)
	
		
		
		startCamera = tdu.Camera()
		startCamera.setTransform(baseMat)
		
		targetCamera = tdu.Camera()
		targetCamera.setTransform(targetMat)

		
		blendCam = startCamera.blendCamera(targetCamera, blendValue)
		if spinning:
			self.spinStartMatrix = blendCam.transform()
		else:
			self.CameraTransform = blendCam.transform()
				
		#print(blendCam.transform())

	def onViewMenuChoice(self, info):
	
		itemName = info['item']
	
		if itemName[0:4] == "Home":
			self.Home()
		
		elif itemName[0:5] == "Frame":
			self.Frame()
		
		elif itemName[0:3] == "Top":
			self.Top()
		
		elif itemName[0:5] == "Right":
			self.Right()
			
		elif itemName[0:4] == "Left":
			self.Left()
		
		elif itemName[0:5] == "Front":
			self.Front()
			
		elif itemName[0:4] == "Back":
			self.Back()
			
		elif itemName[0:6] == "Bottom":
			self.Bottom()
			
		elif itemName == "Set Home Angle":
			self.SetHomeToCurrent()
			
		elif itemName == "Parameters...":
			self.ownerComp.openParameters()
	
		elif itemName == "Navigation Mode":
		
			modeStates = {}
			subMenuItems = parent().par.Navigationmode.menuLabels
			
			for i in range(len(subMenuItems)):
				modeStates[ subMenuItems[i] ] = i == parent().par.Navigationmode.menuIndex
		
			op.TDResources.op('popMenu').OpenSubMenu( subMenuItems, 
									callback=self.onViewMenuChoice, 
									checkedItems=modeStates )
		
		elif itemName == "Presets":
		
			subMenuItems = [ 'Preset {}'.format(i) for i in range(0, self.ownerComp.seq['Preset'].numBlocks) ]
			shortcuts = {}
			for i in subMenuItems:
				shortcuts[i] = str(subMenuItems.index(i) + 1)
			op.TDResources.op('popMenu').OpenSubMenu( 
										subMenuItems, 
										callback=self.onViewMenuChoice,
										shortcuts=shortcuts )
		
		elif itemName.startswith('Preset '):
			presetIndex = tdu.digits(itemName)
			parent.Camera.SetPosAndAngle(
				self.ownerComp.seq['Preset'][presetIndex].parGroup.Pos,
				self.ownerComp.seq['Preset'][presetIndex].parGroup.Angle )
	
		else:
		
			if itemName in parent().par.Navigationmode.menuLabels:
				parent().par.Navigationmode.menuIndex = parent().par.Navigationmode.menuLabels.index(itemName)
		
		return		
		
	def OpenViewMenu(self):
	
		menuItems = [ 	'Navigation Mode', \
						'Home All', \
						'Frame All',\
						'Front',\
						'Top',\
						'Right',\
						'Left',\
						'Back',\
						'Bottom',\
						'Presets',\
						'Set Home Angle',\
						'Parameters...' ]
		
		shortcuts = {	'Home All': 'h',
						'Frame All': 'f',
						'Front': 'n',
						'Top': 't',
						'Right': 'r',
						'Left': 'l',
						'Back': 'k',
						'Bottom': 'b'
					}
	
		op.TDResources.op('popMenu').Open(
							menuItems, 
							callback=self.onViewMenuChoice, 
							shortcuts=shortcuts,
							allowStickySubMenus=False,
							dividersAfterItems=[ menuItems[0], menuItems[9] ], 
							subMenuItems=[ menuItems[0], menuItems[9] ] )
		
		return
		
		
	def SendCallback(self, u, v, valueName, pressed, action, cameraMoved ):

		# check that callbacks are available		
		if not parent.Camera.par.Enablecallbacks:
			return False

		callbackDat = parent.Camera.par.Callbackdat.eval()

		# look for our callback function and raise an error if its not found in the dat		
		if callbackDat is not None:
		
			try:
			
				func = mod( callbackDat.path ).onEvent
				
			except:
				raise RuntimeError("Callback function 'onEvent' not found in callback DAT") from None
			
			else:
				
				event = { 	
					'u':u, 
					'v':v, 
					'valueName': valueName, 
					'pressed': pressed, 
					'action': action, 
					'cameraMoved': cameraMoved,
					'pickOp': None,
					'pickPos': tdu.Position(),
					'pickTexture': tdu.Position(),
					'pickColor': tdu.Color(),
					'pickDepth': 0,
					'pickInstanceId' : 0,
					'pickCustom' : {}
				}
				
				
				if parent.Camera.par.Callbackpickop or parent.Camera.par.Callbackpickuv or parent.Camera.par.Callbackpickcolor or\
					parent.Camera.par.Callbackpicknormal != 0 or parent.Camera.par.Callbackpickdepth or parent.Camera.par.Callbackpickinstanceid or\
					parent.Camera.par.Callbackpickcustomname1 or parent.Camera.par.Callbackpickcustomname2 or parent.Camera.par.Callbackpickcustomname3 or parent.Camera.par.Callbackpickcustomname4:
					
					pickNode = op('renderpick1')
					pickEvent = pickNode.pick(u, v)
					#print(pickEvent)
			
					event['pickOp'] = pickEvent.pickOp
					event['pickPos'] = pickEvent.pos
					event['pickTexture'] = pickEvent.texture
					event['pickColor'] = pickEvent.color
					event['pickNormal'] = pickEvent.normal
					event['pickDepth'] = pickEvent.depth
					event['pickInstanceId'] = pickEvent.instanceId
					event['pickCustom'] = pickEvent.custom
				
				return func( parent.Camera, event )
	
		return False
		