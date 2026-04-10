import clsx from "clsx";

const variants = {
  primary: "border border-[color:var(--accent)] bg-[linear-gradient(135deg,var(--accent),var(--accent-2))] text-[#22130a] shadow-[0_16px_30px_rgba(214,161,108,0.24)] hover:-translate-y-0.5 hover:shadow-[0_18px_34px_rgba(214,161,108,0.3)]",
  ghost: "border border-border bg-bg3/80 text-text hover:border-[color:var(--border-strong)] hover:bg-bg2",
  danger: "bg-red text-[#2b0f0f] border border-red hover:opacity-90",
};

const sizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-5 text-base",
};

const Button = ({
  children,
  className,
  variant = "primary",
  size = "md",
  isLoading = false,
  type = "button",
  ...props
}) => (
  <button
    type={type}
    className={clsx(
      "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-50",
      variants[variant],
      sizes[size],
      className
    )}
    {...props}
  >
    {isLoading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" /> : null}
    {children}
  </button>
);

export default Button;
