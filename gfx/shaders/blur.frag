#version 330 core
in vec2 vUV;
out vec4 FragColor;
uniform sampler2D uTex;
uniform vec2 uDirection;
uniform vec2 uTexelSize;
void main() {
    // Gaussian 9-tap
    float w[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
    vec3 result = texture(uTex, vUV).rgb * w[0];
    for (int i = 1; i < 5; ++i) {
        vec2 off = uDirection * uTexelSize * float(i);
        result += texture(uTex, vUV + off).rgb * w[i];
        result += texture(uTex, vUV - off).rgb * w[i];
    }
    FragColor = vec4(result, 1.0);
}
