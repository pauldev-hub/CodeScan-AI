import Card from "../../components/Common/Card";

const AdminIncidentsPage = () => (
  <main className="space-y-4">
    <Card>
      <h1 className="text-xl font-bold text-text">Security Incidents</h1>
      <p className="mt-2 text-sm text-text2">
        Review escalated findings, assign owners, and track remediation progress from discovery to closure.
      </p>
    </Card>

    <Card>
      <h2 className="text-lg font-bold text-text">Planned Actions</h2>
      <ul className="mt-2 space-y-1 text-sm text-text2">
        <li>- Assign owner to critical incidents</li>
        <li>- Track mitigation status</li>
        <li>- Link incidents to scan IDs and timestamps</li>
        <li>- Export incident summaries for audit</li>
      </ul>
    </Card>
  </main>
);

export default AdminIncidentsPage;
