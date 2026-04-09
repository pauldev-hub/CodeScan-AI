import Card from "../../components/Common/Card";

const AdminQueuePage = () => (
  <main className="space-y-4">
    <Card>
      <h1 className="text-xl font-bold text-text">Scan Queue Monitor</h1>
      <p className="mt-2 text-sm text-text2">
        Track task depth, worker health, and backlog age to keep scan processing latency inside SLO.
      </p>
    </Card>

    <Card>
      <h2 className="text-lg font-bold text-text">Planned Metrics</h2>
      <ul className="mt-2 space-y-1 text-sm text-text2">
        <li>- Pending scan count</li>
        <li>- Running scan count</li>
        <li>- Average queue wait time</li>
        <li>- Worker heartbeat and last processed task</li>
      </ul>
    </Card>
  </main>
);

export default AdminQueuePage;
