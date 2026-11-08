#version 330 core
in vec2 v_uv;
in vec3 v_normal;
in vec3 v_viewDir;

uniform float u_time;
uniform vec3 u_color;

out vec4 FragColor;

void main() {
    // Grelha de energia (linhas finas via fract)
    vec2 g = fract(v_uv * 20.0);
    float grid = max(step(0.92, g.x), step(0.92, g.y));

    // Linha de scan cíclica no eixo Y
    float scan = pow(0.5 + 0.5 * sin(v_uv.y * 5.0 - u_time * 4.0), 8.0);

    // Fresnel: translúcido de frente, brilho nas bordas
    vec3 n = normalize(v_normal);
    vec3 v = normalize(v_viewDir);
    float fresnel = pow(1.0 - max(dot(n, v), 0.0), 3.0);

    float energy = grid * 0.55 + scan * 0.9 + fresnel;
    vec3 rgb = u_color * energy;
    float alpha = clamp(0.1 + fresnel * 0.4 + scan * 0.25 + grid * 0.15, 0.1, 0.7);
    FragColor = vec4(rgb, alpha);
}
