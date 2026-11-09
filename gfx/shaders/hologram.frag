#version 330 core
in vec2 v_uv;
in vec3 v_normal;
in vec3 v_viewDir;
in vec3 v_worldPos;

uniform float u_time;
uniform vec3 u_color;
uniform float u_height;

layout(location = 0) out vec4 FragColor;
layout(location = 1) out vec4 BrightColor;

void main() {
    float h = max(u_height, 0.8);
    float yn = clamp(v_worldPos.y / h, 0.0, 1.0);

    // Coordenada horizontal em espaço de mundo → grelha contínua entre segmentos conectados
    float horiz = v_worldPos.x + v_worldPos.z;
    vec2 g = fract(vec2(horiz * 6.0, v_worldPos.y * 6.0));
    float gx = smoothstep(0.88, 0.96, g.x) + (1.0 - smoothstep(0.0, 0.08, g.x));
    float gy = smoothstep(0.88, 0.96, g.y) + (1.0 - smoothstep(0.0, 0.08, g.y));
    float grid = clamp(max(gx, gy), 0.0, 1.0);

    // Linhas de scan ascendentes + onda secundária
    float scan1 = pow(0.5 + 0.5 * sin(v_worldPos.y * 8.0 - u_time * 3.8 + horiz * 0.7), 6.0);
    float scan2 = 0.5 + 0.5 * sin(v_worldPos.y * 28.0 + u_time * 9.0);

    // Borda inferior (junto ao trilho emissor) e filete de topo
    float bottomGlow = exp(-yn * 4.5);
    float topRim = smoothstep(0.86, 0.98, yn) * (1.0 - smoothstep(0.98, 1.0, yn));
    float vertFade = mix(1.0, 0.42, smoothstep(0.15, 0.95, yn));

    // Fresnel: translúcido de frente, intenso nas bordas e no topo
    vec3 n = normalize(v_normal);
    vec3 v = normalize(v_viewDir);
    float fresnel = pow(1.0 - abs(dot(n, v)), 2.2);

    float flicker = 0.94 + 0.06 * sin(u_time * 23.0 + horiz * 3.1);

    float energy = (grid * 0.42 + scan1 * 0.65 + scan2 * 0.08 + fresnel * 0.85 + bottomGlow * 0.75 + topRim * 1.1)
                   * vertFade * flicker;
    vec3 rgb = u_color * (0.35 + energy * 1.15);
    float alpha = clamp((0.14 + fresnel * 0.34 + grid * 0.16 + scan1 * 0.18 + bottomGlow * 0.28 + topRim * 0.35) * vertFade, 0.10, 0.78);

    FragColor = vec4(rgb, alpha);
    float lum = dot(rgb, vec3(0.2126, 0.7152, 0.0722));
    BrightColor = vec4(lum > 0.95 ? rgb * alpha * 0.65 : vec3(0.0), 1.0);
}
