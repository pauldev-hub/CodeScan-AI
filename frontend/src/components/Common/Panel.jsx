import clsx from "clsx";

const Panel = ({ title, description, className, children }) => (
  <section className={clsx("rounded-[10px] border border-border bg-bg2 p-4", className)}>
    {title ? <h2 className="font-syne text-lg font-bold text-text">{title}</h2> : null}
    {description ? <p className="mt-1 text-sm text-text2">{description}</p> : null}
    <div className={title || description ? "mt-4" : ""}>{children}</div>
  </section>
);

export default Panel;
