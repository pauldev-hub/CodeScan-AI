import clsx from "clsx";

const Panel = ({ title, description, className, children }) => (
  <section className={clsx("codescan-glass rounded-[24px] bg-[color:var(--panel)] p-5 md:p-6", className)}>
    {title ? <h2 className="font-syne text-lg font-bold text-text md:text-[1.25rem]">{title}</h2> : null}
    {description ? <p className="mt-1 text-sm text-text2">{description}</p> : null}
    <div className={title || description ? "mt-4" : ""}>{children}</div>
  </section>
);

export default Panel;
