out vec3 vWorldSpacePos;
out vec3 vCamPos;

void main() 
{
	vec3 camPos = uTDMats[TDCameraIndex()].camInverse[3].xyz;
	vec4 worldSpacePos = TDDeform(TDPos());
	
	gl_Position = TDWorldToProj(worldSpacePos);
	
#ifndef TD_PICKING_ACTIVE
	vCamPos = camPos;
	vWorldSpacePos = worldSpacePos.xyz;	
#else // TD_PICKING_ACTIVE
	// This will automatically write out the nessessary values
	// for this shader to work with picking.
	// See the documentation if you want to write custom values for picking.
	TDWritePickingValues();
#endif // TD_PICKING_pACTIVE
}

