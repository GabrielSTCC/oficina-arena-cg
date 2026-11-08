#version 330 core
in vec2 vUV;
out vec4 FragColor;
uniform sampler2D uScene;
uniform float uThreshold;
void main() {
    vec3 c = texture(uScene, vUV).rgb;
    float b = max(c.r, max(c.g, c.b));
    FragColor = vec4(b > uThreshold ? c : vec3(0.0), 1.0);
}
