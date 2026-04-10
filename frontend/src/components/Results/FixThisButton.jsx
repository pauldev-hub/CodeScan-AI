import Button from "../Common/Button";

const FixThisButton = ({ loading, disabled, onClick }) => (
  <Button size="sm" variant="ghost" isLoading={loading} disabled={disabled} onClick={onClick}>
    Fix This For Me
  </Button>
);

export default FixThisButton;
