#version 330 core
in vec2 vUV;
out vec4 FragColor;
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uStrength;
uniform float uExposure;

vec3 aces_tonemap(vec3 x) {
    const float a = 2.51;
    const float b = 0.03;
    const float c = 2.43;
    const float d = 0.59;
    const float e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

void main() {
    vec3 hdr = texture(uScene, vUV).rgb + texture(uBloom, vUV).rgb * uStrength;
    float exposure = uExposure > 0.0 ? uExposure : 1.35;
    vec3 mapped = aces_tonemap(hdr * exposure);

    // Leve ganho de saturação
    float luma = dot(mapped, vec3(0.2126, 0.7152, 0.0722));
    mapped = mix(vec3(luma), mapped, 1.08);

    // Vinheta suave nas bordas da tela
    vec2 d = vUV - 0.5;
    float vig = 1.0 - dot(d, d) * 0.38;
    mapped *= clamp(vig, 0.72, 1.0);

    // Gamma correction
    mapped = pow(max(mapped, vec3(0.0)), vec3(1.0 / 2.2));
    FragColor = vec4(mapped, 1.0);
}
