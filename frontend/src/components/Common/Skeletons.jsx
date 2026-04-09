const pulse = "animate-pulse rounded-md bg-bg3";

export const ScoreRingSkeleton = () => <div className={`${pulse} h-24 w-24 rounded-full`} />;

export const StatCardSkeleton = () => (
  <div className="rounded-[10px] border border-border bg-bg2 p-4">
    <div className={`${pulse} h-3 w-20`} />
    <div className={`${pulse} mt-3 h-8 w-14`} />
  </div>
);

export const FindingCardSkeleton = () => (
  <div className="rounded-[10px] border border-border bg-bg2 p-4">
    <div className={`${pulse} h-3 w-24`} />
    <div className={`${pulse} mt-3 h-4 w-2/3`} />
    <div className={`${pulse} mt-2 h-3 w-full`} />
    <div className={`${pulse} mt-2 h-3 w-5/6`} />
  </div>
);

export const ChatBubbleSkeleton = () => <div className={`${pulse} h-10 w-2/3 rounded-xl`} />;
