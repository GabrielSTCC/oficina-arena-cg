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

uniform vec3 uDirLightDir;
uniform vec3 uDirLightColor;

uniform int uNumPoints;
uniform vec3 uPointPos[8];
uniform vec3 uPointColor[8];

uniform mat4 uLightVP;
uniform sampler2D uShadowMap;
uniform int uUseShadows;

uniform vec3 uFogColor;
uniform float uFogStart;
uniform float uFogEnd;

uniform float uBloomThreshold;
uniform float uSpecScale;

vec3 cotangent_frame(vec3 N, vec3 p, vec2 uv) {
    vec3 dp1 = dFdx(p);
    vec3 dp2 = dFdy(p);
    vec2 duv1 = dFdx(uv);
    vec2 duv2 = dFdy(uv);
    vec3 dp2perp = cross(dp2, N);
    vec3 dp1perp = cross(N, dp1);
    vec3 T = dp2perp * duv1.x + dp1perp * duv2.x;
    vec3 B = dp2perp * duv1.y + dp1perp * duv2.y;
    float invmax = inversesqrt(max(dot(T, T), dot(B, B)));
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
    float bias = max(0.004 * (1.0 - dot(N, L)), 0.0015);
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
    vec3 N = normalize(vNormal);
    if (uUseNormalMap == 1) {
        N = normalize(cotangent_frame(N, vWorldPos, vUV));
    }
    vec3 V = normalize(uViewPos - vWorldPos);
    vec3 tex = vec3(1.0);
    if (uUseTexture == 1) {
        tex = texture(uTexture, vUV).rgb;
    }
    vec3 base = uKd * tex;
    float specScale = uSpecScale > 0.0 ? uSpecScale : 0.22;

    vec3 ambient = 0.02 * base;
    vec3 Ldir = normalize(-uDirLightDir);
    float diff = max(dot(N, Ldir), 0.0);
    vec3 H = normalize(Ldir + V);
    float spec = pow(max(dot(N, H), 0.0), uShininess) * specScale;
    float sh = shadow_factor(vWorldPos, N, Ldir);
    vec3 color = ambient + sh * (diff * uDirLightColor * base + spec * uDirLightColor * uKs);

    for (int i = 0; i < 8; ++i) {
        if (i >= uNumPoints) break;
        vec3 Lvec = uPointPos[i] - vWorldPos;
        float dist = length(Lvec);
        vec3 L = Lvec / max(dist, 1e-4);
        float atten = 1.0 / (1.0 + 0.09 * dist + 0.032 * dist * dist);
        float d = max(dot(N, L), 0.0);
        vec3 Hp = normalize(L + V);
        float s = pow(max(dot(N, Hp), 0.0), uShininess) * specScale;
        color += 0.65 * atten * (d * uPointColor[i] * base + s * uPointColor[i] * uKs);
    }

    color += uEmissive * tex;

    float distCam = length(uViewPos - vWorldPos);
    float fogFactor = clamp((uFogEnd - distCam) / max(uFogEnd - uFogStart, 1e-3), 0.0, 1.0);
    color = mix(uFogColor, color, fogFactor);

    // HDR → RT0; bloom mask → RT1 (só luminância alta)
    float thr = uBloomThreshold > 0.0 ? uBloomThreshold : 1.2;
    float lum = dot(color, vec3(0.2126, 0.7152, 0.0722));
    BrightColor = vec4(lum > thr ? color : vec3(0.0), 1.0);
    FragColor = vec4(color, uAlpha);
}
