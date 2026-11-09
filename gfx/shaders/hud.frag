#version 330 core
in vec2 vUV;
out vec4 FragColor;

uniform sampler2D uHud;

void main() {
    // Pillow tem (0,0) no canto superior esquerdo; invertemos Y no sample
    vec4 col = texture(uHud, vec2(vUV.x, 1.0 - vUV.y));
    if (col.a < 0.004) discard;
    FragColor = col;
}
