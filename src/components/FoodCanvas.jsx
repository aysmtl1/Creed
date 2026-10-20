import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF, OrbitControls, Float } from '@react-three/drei';

// 3D Model Doku ve Geometri Yükleyici
function Model({ modelPath }) {
  const { scene } = useGLTF(modelPath);
  const modelRef = useRef();

  // Modeli sürekli kendi etrafında yavaşça döndürme animasyonu
  useFrame((state, delta) => {
    if (modelRef.current) {
      modelRef.current.rotation.y += delta * 0.5;
    }
  });

  return <primitive ref={modelRef} object={scene} scale={1.5} />;
}

export default function FoodCanvas({ modelPath = '/models/food_bowl.glb' }) {
  return (
    <div className="w-full h-64 md:h-80 relative cursor-grab active:cursor-grabbing">
      <Canvas camera={{ position: [0, 0, 5], fov: 45 }}>
        {/* Ortam Işıkları */}
        <ambientLight intensity={0.8} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} />
        <pointLight position={[-5, -5, -5]} intensity={0.5} />

        {/* Modeli Havada Süzülür/Dalgalanır Gibi Hissettiren Efekt */}
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <Model modelPath={modelPath} />
        </Float>

        {/* Kullanıcının Fareyle Modeli Dündürmesini Sağlayan Kontrol */}
        <OrbitControls enableZoom={false} autoRotate={false} />
      </Canvas>
    </div>
  );
}