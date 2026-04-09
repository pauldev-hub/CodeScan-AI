import clsx from "clsx";

const Card = ({ children, className }) => (
  <div className={clsx("rounded-[10px] border border-border bg-bg2 p-4 shadow-sm", className)}>{children}</div>
);

export default Card;
