#version 330 core
in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUV;

layout(location = 0) out vec4 FragColor;
layout(location = 1) out vec4 BrightColor;

uniform vec3 uViewPos;
uniform vec3 uKd;
uniform vec3 uKs;
uniform float uShininess;
uniform float uAlpha;
uniform int uUseTexture;
uniform sampler2D uTexture;
uniform vec3 uEmissive;

uniform int uUseNormalMap;
uniform sampler2D uNormalMap;

uniform int uUseEmissiveMap;
uniform sampler2D uEmissiveMap;
uniform float uPulseHz;
uniform int uAlphaTex;
uniform float uTriplanarScale;

uniform float uTime;
uniform vec3 uSkyAmbient;
uniform vec3 uGroundAmbient;

uniform int uFloorMode;
uniform sampler2D uCellMap;
uniform vec2 uGridSize;

uniform vec3 uDirLightDir;
uniform vec3 uDirLightColor;

uniform int uNumPoints;
uniform vec3 uPointPos[16];
uniform vec3 uPointColor[16];

uniform mat4 uLightVP;
uniform sampler2D uShadowMap;
uniform int uUseShadows;

uniform vec3 uFogColor;
uniform float uFogStart;
uniform float uFogEnd;

uniform float uBloomThreshold;
uniform float uSpecScale;

float cell_hash(vec2 c) {
    return fract(sin(dot(c, vec2(127.1, 311.7))) * 43758.5453);
}

vec2 triplanar_uv(vec3 wp, vec3 n, float scale) {
    vec3 an = abs(n);
    if (an.x >= an.y && an.x >= an.z) {
        return wp.zy * scale;
    } else if (an.z >= an.x && an.z >= an.y) {
        return wp.xy * scale;
    }
    return wp.xz * scale;
}

vec2 floor_tile_uv(vec3 wp) {
    vec2 cell = floor(wp.xz);
    vec2 f = fract(wp.xz) - 0.5;
    float h = floor(cell_hash(cell) * 4.0);
    if (h == 1.0) f = vec2(-f.y, f.x);
    else if (h == 2.0) f = -f;
    else if (h == 3.0) f = vec2(f.y, -f.x);
    return f + 0.5;
}

vec3 cotangent_frame(vec3 N, vec3 p, vec2 uv) {
    vec3 dp1 = dFdx(p);
    vec3 dp2 = dFdy(p);
    vec2 duv1 = dFdx(uv);
    vec2 duv2 = dFdy(uv);
    vec3 dp2perp = cross(dp2, N);
    vec3 dp1perp = cross(N, dp1);
    vec3 T = dp2perp * duv1.x + dp1perp * duv2.x;
    vec3 B = dp2perp * duv1.y + dp1perp * duv2.y;
    float invmax = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-8));
    return mat3(T * invmax, B * invmax, N) * (texture(uNormalMap, uv).xyz * 2.0 - 1.0);
}

float shadow_factor(vec3 worldPos, vec3 N, vec3 L) {
    if (uUseShadows == 0) return 1.0;
    vec4 ls = uLightVP * vec4(worldPos, 1.0);
    vec3 proj = ls.xyz / ls.w;
    proj = proj * 0.5 + 0.5;
    if (proj.z > 1.0 || proj.x < 0.0 || proj.x > 1.0 || proj.y < 0.0 || proj.y > 1.0) {
        return 1.0;
    }
    float bias = max(0.0035 * (1.0 - dot(N, L)), 0.0012);
    float shadow = 0.0;
    vec2 texel = 1.0 / vec2(textureSize(uShadowMap, 0));
    for (int x = -1; x <= 1; ++x) {
        for (int y = -1; y <= 1; ++y) {
            float closest = texture(uShadowMap, proj.xy + vec2(x, y) * texel).r;
            shadow += (proj.z - bias > closest) ? 0.0 : 1.0;
        }
    }
    return shadow / 9.0;
}

void main() {
    vec3 N0 = normalize(vNormal);
    vec2 uv = vUV;
    if (uFloorMode == 1) {
        uv = floor_tile_uv(vWorldPos);
    } else if (uTriplanarScale > 0.0) {
        uv = triplanar_uv(vWorldPos, N0, uTriplanarScale);
    }

    vec3 N = N0;
    if (uUseNormalMap == 1) {
        N = normalize(cotangent_frame(N0, vWorldPos, uv));
    }
    vec3 V = normalize(uViewPos - vWorldPos);

    vec4 texSample = vec4(1.0);
    if (uUseTexture == 1) {
        texSample = texture(uTexture, uv);
    }
    float outAlpha = uAlpha * (uAlphaTex == 1 ? texSample.a : 1.0);
    if (outAlpha < 0.01) discard;

    vec3 tex = texSample.rgb;
    vec3 base = uKd * tex;

    float ao = 1.0;
    vec3 floorEmissive = vec3(0.0);
    if (uFloorMode == 1) {
        vec2 cell = floor(vWorldPos.xz);
        float hv = cell_hash(cell + vec2(19.3, 7.1));
        base *= (0.93 + 0.14 * hv);

        vec2 gsz = max(uGridSize, vec2(1.0));
        vec2 cuv = clamp(vWorldPos.xz / gsz, vec2(0.001), vec2(0.999));
        vec4 cm = texture(uCellMap, cuv);
        // R: paredes (AO de contato), G: armadilhas, B: base Alfa, A: base Beta
        ao = 1.0 - 0.42 * cm.r;
        floorEmissive += vec3(0.85, 0.14, 0.05) * cm.g * 0.22;
        floorEmissive += vec3(0.18, 0.78, 1.05) * cm.b * 0.28;
        floorEmissive += vec3(1.05, 0.36, 0.12) * cm.a * 0.28;

        // Grade tática sutil nas bordas das células 15x9
        vec2 gf = abs(fract(vWorldPos.xz) - 0.5);
        float edgeDist = 0.5 - max(gf.x, gf.y);
        float fw = max(fwidth(vWorldPos.x), fwidth(vWorldPos.z));
        float gridLine = 1.0 - smoothstep(0.008, 0.022 + fw * 0.8, edgeDist);
        bool inBounds = (vWorldPos.x >= 0.0 && vWorldPos.x <= gsz.x &&
                         vWorldPos.z >= 0.0 && vWorldPos.z <= gsz.y);
        if (inBounds) {
            vec3 lineCol = mix(vec3(0.14, 0.58, 0.78), vec3(0.95, 0.32, 0.16), clamp(cm.g + cm.a, 0.0, 1.0));
            floorEmissive += lineCol * gridLine * 0.32;
            // Cruz discreta nos cantos de célula
            float corner = 1.0 - smoothstep(0.03, 0.065, length(0.5 - gf));
            floorEmissive += lineCol * corner * 0.22;
        }
    }

    float specScale = uSpecScale > 0.0 ? uSpecScale : 0.25;
    vec3 skyAmb = length(uSkyAmbient) > 0.0 ? uSkyAmbient : vec3(0.16, 0.20, 0.28);
    vec3 gndAmb = length(uGroundAmbient) > 0.0 ? uGroundAmbient : vec3(0.06, 0.07, 0.09);
    vec3 hemi = mix(gndAmb, skyAmb, clamp(N.y * 0.5 + 0.5, 0.0, 1.0));
    vec3 ambient = hemi * base * ao;

    vec3 Ldir = normalize(-uDirLightDir);
    float diff = max(dot(N, Ldir), 0.0);
    vec3 H = normalize(Ldir + V);
    float spec = pow(max(dot(N, H), 0.0), uShininess) * specScale;
    float sh = shadow_factor(vWorldPos, N, Ldir);
    vec3 color = ambient + sh * (diff * uDirLightColor * base + spec * uDirLightColor * uKs);

    for (int i = 0; i < 16; ++i) {
        if (i >= uNumPoints) break;
        vec3 Lvec = uPointPos[i] - vWorldPos;
        float dist = length(Lvec);
        vec3 L = Lvec / max(dist, 1e-4);
        float atten = 1.0 / (1.0 + 0.08 * dist + 0.028 * dist * dist);
        float d = max(dot(N, L), 0.0);
        vec3 Hp = normalize(L + V);
        float s = pow(max(dot(N, Hp), 0.0), uShininess) * specScale;
        color += 0.70 * atten * (d * uPointColor[i] * base * ao + s * uPointColor[i] * uKs);
    }

    float pulse = 1.0;
    if (uPulseHz > 0.0) {
        pulse = 0.62 + 0.38 * sin(uTime * uPulseHz * 6.2831853);
    }
    vec3 emMask = (uUseEmissiveMap == 1) ? texture(uEmissiveMap, uv).rgb : tex;
    color += uEmissive * emMask * pulse + floorEmissive;

    float distCam = length(uViewPos - vWorldPos);
    float fogFactor = clamp((uFogEnd - distCam) / max(uFogEnd - uFogStart, 1e-3), 0.0, 1.0);
    color = mix(uFogColor, color, fogFactor);

    // HDR → RT0; bloom mask → RT1 (só luminância alta)
    float thr = uBloomThreshold > 0.0 ? uBloomThreshold : 1.15;
    float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
    BrightColor = vec4(lum > thr ? color * outAlpha : vec3(0.0), 1.0);
    FragColor = vec4(color, outAlpha);
}
