import beanImg from "../assets/bean.png";

// Kesim, fotoğraftaki yarığı (sağ üstten sol alta) takip eden tırtıklı bir çizgidir.
// İki yarı aynı noktaları kullandığı için birleşince çekirdek bütün görünür.
const CUT_L = "polygon(0 0, 69.7% 0.0%, 63.2% 8.0%, 63.3% 19.1%, 54.2% 26.0%, 55.3% 37.5%, 46.5% 44.5%, 47.0% 55.8%, 37.8% 62.6%, 37.8% 73.7%, 29.0% 80.6%, 29.6% 92.0%, 23.1% 100.0%, 0 100%)";
const CUT_R = "polygon(69.7% 0.0%, 63.2% 8.0%, 63.3% 19.1%, 54.2% 26.0%, 55.3% 37.5%, 46.5% 44.5%, 47.0% 55.8%, 37.8% 62.6%, 37.8% 73.7%, 29.0% 80.6%, 29.6% 92.0%, 23.1% 100.0%, 100% 100%, 100% 0)";

export default function Bean({ side }) {
  const isLeft = side === "l";
  return (
    <img
      src={beanImg}
      alt=""
      aria-hidden="true"
      draggable={false}
      className={`half-${side} absolute select-none`}
      style={{ width: "min(70vh, 120vw)", height: "min(70vh, 120vw)", clipPath: isLeft ? CUT_L : CUT_R }}
    />
  );
}
