import * as THREE from
"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js";

const container = document.getElementById("ultron-canvas");

if (!container) {
  throw new Error("ULTRON canvas not found");
}

// SCENE
const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
  35,
  container.clientWidth / container.clientHeight,
  0.1,
  100
);

camera.position.set(0, 0, 5.2);

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true
});

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(container.clientWidth, container.clientHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.5;

container.appendChild(renderer.domElement);

// LIGHTING
scene.add(new THREE.AmbientLight(0x87909c, 2));

function addLight(color, intensity, x, y, z) {
  const light = new THREE.PointLight(color, intensity, 15);
  light.position.set(x, y, z);
  scene.add(light);
}

addLight(0xff001c, 65, 0, 1, 3);
addLight(0x9baac5, 90, -3, 2, 3);
addLight(0xff142f, 80, 3, 0, 2);
addLight(0x343c55, 90, 0, 2, -3);

// MATERIALS
const titanium = new THREE.MeshStandardMaterial({
  color: 0x929ba5,
  metalness: 0.95,
  roughness: 0.24
});

const darkMetal = new THREE.MeshStandardMaterial({
  color: 0x171a20,
  metalness: 0.95,
  roughness: 0.3
});

const silver = new THREE.MeshStandardMaterial({
  color: 0xd4d9e0,
  metalness: 0.95,
  roughness: 0.2
});

const redMetal = new THREE.MeshStandardMaterial({
  color: 0x720015,
  metalness: 0.9,
  roughness: 0.25,
  emissive: 0x42000c,
  emissiveIntensity: 0.8
});

const eyeMaterial = new THREE.MeshStandardMaterial({
  color: 0xff001e,
  emissive: 0xff001e,
  emissiveIntensity: 5
});

// HEAD
const head = new THREE.Group();
scene.add(head);

function sphere(parent, material, pos, scale) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(1, 48, 32),
    material
  );

  mesh.position.set(...pos);
  mesh.scale.set(...scale);
  parent.add(mesh);

  return mesh;
}

function box(parent, material, pos, size, rotation = 0) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(...size),
    material
  );

  mesh.position.set(...pos);
  mesh.rotation.z = rotation;
  parent.add(mesh);

  return mesh;
}

// METALLIC SKULL
sphere(head, titanium, [0, 0.05, 0], [0.88, 1.18, 0.58]);

sphere(head, silver, [0, 0.78, 0.25], [0.69, 0.34, 0.35]);

// FOREHEAD REACTOR
sphere(head, darkMetal, [0, 0.78, 0.57], [0.18, 0.14, 0.06]);

sphere(head, eyeMaterial, [0, 0.78, 0.625], [0.075, 0.045, 0.025]);

// EYES
const eyes = [];

for (const side of [-1, 1]) {
  const x = side * 0.38;

  sphere(head, darkMetal, [x, 0.29, 0.48], [0.30, 0.22, 0.16]);

  sphere(head, redMetal, [x, 0.29, 0.59], [0.245, 0.155, 0.08]);

  const eye = sphere(
    head,
    eyeMaterial,
    [x, 0.29, 0.66],
    [0.15, 0.085, 0.045]
  );

  eyes.push(eye);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(0.19, 0.018, 8, 48),
    silver
  );

  ring.position.set(x, 0.29, 0.64);
  head.add(ring);

  box(head, darkMetal, [x, 0.52, 0.56], [0.52, 0.10, 0.16], side * -0.16);

  box(head, silver, [x, 0.57, 0.54], [0.40, 0.035, 0.09], side * -0.16);
}

// NOSE
sphere(head, darkMetal, [0, -0.02, 0.57], [0.18, 0.37, 0.17]);

sphere(head, silver, [0, -0.17, 0.68], [0.17, 0.13, 0.10]);

// CHEEKS AND SIDE ARMOR
for (const side of [-1, 1]) {
  sphere(head, silver, [side * 0.65, -0.17, 0.32], [0.24, 0.43, 0.20]);

  sphere(head, darkMetal, [side * 0.72, -0.35, 0.43], [0.17, 0.23, 0.12]);

  for (let i = 0; i < 4; i++) {
    box(
      head,
      redMetal,
      [side * 0.72, -0.12 - i * 0.075, 0.55],
      [0.13, 0.018, 0.025],
      side * 0.2
    );
  }

  sphere(head, darkMetal, [side * 0.82, 0.23, 0], [0.15, 0.43, 0.42]);

  sphere(head, titanium, [side * 0.88, 0.20, 0.15], [0.11, 0.27, 0.24]);

  sphere(head, redMetal, [side * 0.91, 0.20, 0.34], [0.07, 0.13, 0.07]);
}

// MOVING MECHANICAL JAW
const jaw = new THREE.Group();
jaw.position.set(0, -0.43, 0.48);
head.add(jaw);

sphere(jaw, darkMetal, [0, -0.12, 0], [0.60, 0.35, 0.19]);

sphere(jaw, titanium, [0, -0.26, 0.03], [0.55, 0.17, 0.18]);

for (const side of [-1, 1]) {
  sphere(jaw, redMetal, [side * 0.37, -0.12, 0.14], [0.055, 0.055, 0.035]);

  box(jaw, silver, [side * 0.29, -0.27, 0.15], [0.15, 0.045, 0.04]);
}

// MOUTH
sphere(
  head,
  new THREE.MeshStandardMaterial({ color: 0x020002 }),
  [0, -0.43, 0.62],
  [0.36, 0.075, 0.06]
);

// TEETH
for (let i = -3; i <= 3; i++) {
  box(head, silver, [i * 0.085, -0.41, 0.68], [0.045, 0.045, 0.035]);
}

// CHIN
sphere(jaw, redMetal, [0, -0.37, 0.15], [0.17, 0.055, 0.035]);

// HEAD DETAILS
for (const side of [-1, 1]) {
  box(head, darkMetal, [side * 0.25, 0.93, 0.23], [0.035, 0.25, 0.08], side * 0.25);

  box(head, redMetal, [side * 0.25, 0.96, 0.29], [0.014, 0.16, 0.025], side * 0.25);
}

// MOUSE TRACKING
let mouseX = 0;
let mouseY = 0;
let speaking = false;

window.addEventListener("pointermove", e => {
  mouseX = (e.clientX / window.innerWidth - 0.5) * 0.45;
  mouseY = (e.clientY / window.innerHeight - 0.5) * 0.2;
});

// AI SPEAKING CONTROL
window.setUltronSpeaking = function(value) {
  speaking = Boolean(value);
};

// ANIMATION
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);

  const t = clock.getElapsedTime();

  head.rotation.y += (mouseX - head.rotation.y) * 0.035;
  head.rotation.x += (-mouseY - head.rotation.x) * 0.035;

  head.position.y = Math.sin(t * 1.2) * 0.025;

  const glow = 3.5 + Math.sin(t * 3) * 1.5;

  eyes.forEach(eye => {
    eye.material.emissiveIntensity = glow;
  });

  const movement = speaking
    ? Math.abs(Math.sin(t * 13)) * 0.12
    : 0;

  jaw.rotation.x += (movement - jaw.rotation.x) * 0.2;

  renderer.render(scene, camera);
}

animate();

// RESPONSIVE DISPLAY
const resizeObserver = new ResizeObserver(() => {
  const width = container.clientWidth;
  const height = container.clientHeight;

  if (!width || !height) return;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
});

resizeObserver.observe(container);
