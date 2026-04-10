import { useEffect, useRef, useState } from "react";

const SeverityStatCard = ({ label, value, className = "" }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const animatedRef = useRef(false);

  useEffect(() => {
    const target = Math.max(0, Number(value) || 0);
    if (animatedRef.current) {
      setDisplayValue(target);
      return;
    }

    animatedRef.current = true;
    const startedAt = performance.now();
    const duration = 600;

    let raf = 0;
    const animate = (time) => {
      const elapsed = Math.min(1, (time - startedAt) / duration);
      setDisplayValue(Math.round(target * elapsed));
      if (elapsed < 1) {
        raf = requestAnimationFrame(animate);
      }
    };

    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [value]);

  return (
    <div className={`rounded-lg border border-border bg-bg3 p-3 ${className}`}>
      <p className="text-xs text-text2">{label}</p>
      <p className="mt-1 text-xl font-bold text-text">{displayValue}</p>
    </div>
  );
};

export default SeverityStatCard;
