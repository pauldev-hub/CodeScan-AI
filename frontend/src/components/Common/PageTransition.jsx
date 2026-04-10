const PageTransition = ({ pageKey, children, className = "" }) => (
  <div key={pageKey} className={`codescan-page-enter ${className}`.trim()}>
    {children}
  </div>
);

export default PageTransition;
