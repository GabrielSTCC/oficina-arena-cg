#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProj;
uniform mat3 uNormalMat;
uniform vec3 uViewPos;

out vec2 v_uv;
out vec3 v_normal;
out vec3 v_viewDir;
out vec3 v_worldPos;

void main() {
    vec4 world = uModel * vec4(aPos, 1.0);
    v_uv = aUV;
    v_normal = normalize(uNormalMat * aNormal);
    v_viewDir = uViewPos - world.xyz;
    v_worldPos = world.xyz;
    gl_Position = uProj * uView * world;
}
