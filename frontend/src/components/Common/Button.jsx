import clsx from "clsx";

const variants = {
  primary: "bg-accent text-white border border-accent hover:opacity-90",
  ghost: "bg-bg3 text-text border border-border hover:bg-bg2",
  danger: "bg-red text-white border border-red hover:opacity-90",
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
      "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all duration-200 ease-out disabled:cursor-not-allowed disabled:opacity-50",
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
