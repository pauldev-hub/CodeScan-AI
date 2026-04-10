import clsx from "clsx";

const Card = ({ children, className }) => (
  <div className={clsx("codescan-glass rounded-[22px] bg-[color:var(--panel)] p-5 md:p-6", className)}>{children}</div>
);

export default Card;
