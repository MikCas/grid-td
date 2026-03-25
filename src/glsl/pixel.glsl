// Pristine Infinite Grid Shader for TouchDesigner
// Based on: https://bgolus.medium.com/the-best-darn-grid-shader-yet-727f9278b9d8

// GRID
uniform int   uPlaneMode;    // Grid plane: 0 = XY (Front), 1 = YZ (Right), 2 = ZX (Top)
uniform float uCellSize;     // World-space size of one major grid cell
uniform vec2  uSubdivisions; // Minor cells per major cell (vec2, allows non-square)

// WIDTH 
uniform float uMaxLineWidth; // Maximum line width in UV space (scales all width params)
uniform float uMinWidth;     // Minor grid line width [0–1]
uniform float uMajWidth;     // Major grid line width [0–1]
uniform float uAxisWidth;    // Axis line width [0–1]

// COLOR
uniform vec4  uMinColor;     // Minor grid line color (RGBA)
uniform vec4  uMajColor;     // Major grid line color (RGBA)
uniform vec4  uBgColor;      // Background color (RGBA, alpha = tile opacity)
uniform float uMinOpacity;   // Minor grid line opacity [0–1]
uniform float uFadeDistance;  // Distance (world units) at which the grid fully fades out
uniform vec4  uColorX;       // X-axis color (default: red)
uniform vec4  uColorY;       // Y-axis color (default: green)
uniform vec4  uColorZ;       // Z-axis color (default: blue)

in vec3 vWorldSpacePos;
in vec3 vCamPos;

out vec4 oFragColor;

// ─────────────────────────────────────────────
// Pristine Grid: resolution-independent AA grid
// ─────────────────────────────────────────────
float pristineGrid(vec2 uv, vec2 lineWidth) {
    vec2 ddx = dFdx(uv);
    vec2 ddy = dFdy(uv);
    vec2 uvDeriv = vec2(length(vec2(ddx.x, ddy.x)), length(vec2(ddx.y, ddy.y)));

    vec2 drawWidth = max(lineWidth, uvDeriv);
    vec2 lineAA = uvDeriv * 1.5;
    vec2 gridUV = 1.0 - abs(fract(uv) * 2.0 - 1.0);

    // Anti-aliased line mask
    vec2 grid2 = 1.0 - smoothstep(drawWidth - lineAA, drawWidth + lineAA, gridUV);
    // Sub-pixel fade: gracefully disappear when lines are smaller than a pixel
    grid2 *= clamp(lineWidth / drawWidth, 0.0, 1.0);
    // Mip-level blend: converge to solid fill at extreme distances
    grid2 = mix(grid2, lineWidth, clamp(uvDeriv * 2.0 - 1.0, 0.0, 1.0));

    return mix(grid2.x, 1.0, grid2.y);
}

// ─────────────────────────────────────────────
// Anti-aliased line at uv = 0
// Returns per-axis masks as vec2(x, y)
// ─────────────────────────────────────────────
vec2 axisLine(vec2 uv, float width) {
    vec2 axisW = vec2(width);
    vec2 dAxis = fwidth(uv);
    vec2 drawW = max(axisW, dAxis);
    vec2 aa = dAxis * 1.5;

    vec2 mask = 1.0 - smoothstep(drawW - aa, drawW + aa, abs(uv));
    mask *= clamp(axisW / drawW, 0.0, 1.0); // Sub-pixel fade
    return mask;
}

void main() {
    TDCheckDiscard();

    // UV SETUP
    vec2 uv;
    vec2 fadePlane;
    vec4 axisColorU; // color for the vertical axis line (uv.x = 0)
    vec4 axisColorV; // color for the horizontal axis line (uv.y = 0)
    vec3 wp = vWorldSpacePos;

    if (uPlaneMode == 0) {        // XY plane (Front view)
        uv = wp.xy / uCellSize;
        fadePlane = wp.xy - vCamPos.xy;
        axisColorU = uColorX;     // vertical line = X-axis
        axisColorV = uColorY;     // horizontal line = Y-axis
    } else if (uPlaneMode == 1) { // YZ plane (Right view)
        uv = wp.yz / uCellSize;
        fadePlane = wp.yz - vCamPos.yz;
        axisColorU = uColorY;     // vertical line = Y-axis
        axisColorV = uColorZ;     // horizontal line = Z-axis
    } else {                      // ZX plane (Top view, default)
        uv = wp.xz / uCellSize;
        fadePlane = wp.xz - vCamPos.xz;
        axisColorU = uColorX;     // vertical line = X-axis
        axisColorV = uColorZ;     // horizontal line = Z-axis
    }

    // WIDTH SCALING
    float minW = uMinWidth * uMaxLineWidth;
    float majW = uMajWidth * uMaxLineWidth;
    float axisW = uAxisWidth * uMaxLineWidth;

    // GRID MASKS
    float minorMask = pristineGrid(uv * uSubdivisions, vec2(minW));
    float majorMask = pristineGrid(uv, vec2(majW));

    // AXIS MASKS
    vec2 axisMask = axisLine(uv, axisW);

    // COMPOSITE
    vec4 bg = vec4(uBgColor.rgb * uBgColor.a, uBgColor.a);
    vec4 color = mix(bg, uMinColor, minorMask * uMinOpacity);
    color = mix(color, uMajColor, majorMask);
    color = mix(color, axisColorU, axisMask.x);
    color = mix(color, axisColorV, axisMask.y);

    // DISTANCE FADE
    float dist = length(fadePlane);
    float alphaFade = 1.0 - smoothstep(0.0, uFadeDistance, dist);
    color = mix(bg, color, alphaFade);

    TDAlphaTest(color.a);
    oFragColor = TDOutputSwizzle(color);
}
