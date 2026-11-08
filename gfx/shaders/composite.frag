#version 330 core
in vec2 vUV;
out vec4 FragColor;
uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform float uStrength;
uniform float uExposure;
void main() {
    vec3 hdr = texture(uScene, vUV).rgb + texture(uBloom, vUV).rgb * uStrength;
    float exposure = uExposure > 0.0 ? uExposure : 1.8;
    // Exposure tone mapping
    vec3 mapped = vec3(1.0) - exp(-hdr * exposure);
    // Gamma correction
    mapped = pow(mapped, vec3(1.0 / 2.2));
    FragColor = vec4(mapped, 1.0);
}
