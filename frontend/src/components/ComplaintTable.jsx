import StatusBadge from "./StatusBadge";

const CATEGORY_TO_DEPARTMENT = {
  garbage: "sanitation",
  water: "water",
  electricity: "electrical",
  roads: "public_works",
};

const titleCase = (value) =>
  value?.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function ComplaintTable({
  complaints,
  onHistory,
  onUpdate,
  onAssign,
  authorities = [],
  loading,
}) {
  if (loading) {
    return (
      <div className="empty-state">
        <span className="spinner" /> Loading complaints…
      </div>
    );
  }

  if (!complaints.length) {
    return <div className="empty-state">No complaints match this view.</div>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Issue</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Assigned authority</th>
            <th>Created</th>
            {(onUpdate || onAssign) && <th>Action</th>}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {complaints.map((complaint) => {
            const expectedDept = CATEGORY_TO_DEPARTMENT[complaint.category];
            const eligibleAuthorities = authorities.filter(
              (u) =>
                u.role === "authority" &&
                u.is_active &&
                u.department === expectedDept
            );

            return (
              <tr key={complaint.id}>
                <td>#{complaint.id}</td>
                <td>
                  <strong>{complaint.title}</strong>
                  <span className="table-description">
                    {complaint.description}
                  </span>
                </td>
                <td>{titleCase(complaint.category)}</td>
                <td>{titleCase(complaint.priority)}</td>
                <td>
                  <StatusBadge status={complaint.status} />
                </td>
                <td>
                  {complaint.assigned_authority_id
                    ? `Authority #${complaint.assigned_authority_id}`
                    : "Unassigned"}
                </td>
                <td>
                  {new Date(complaint.created_at).toLocaleDateString()}
                </td>

                {onUpdate && (
                  <td>
                    {complaint.status === "assigned" && (
                      <button
                        className="text-button"
                        onClick={() => onUpdate(complaint.id, "in_progress")}
                      >
                        Start work
                      </button>
                    )}
                    {complaint.status === "in_progress" && (
                      <button
                        className="text-button"
                        onClick={() => onUpdate(complaint.id, "resolved")}
                      >
                        Resolve
                      </button>
                    )}
                  </td>
                )}

                {onAssign && (
                  <td>
                    {complaint.status !== "resolved" ? (
                      <div>
                        <select
                          aria-label={`Assign complaint #${complaint.id}`}
                          value={complaint.assigned_authority_id || ""}
                          onChange={(e) => {
                            if (e.target.value) {
                              onAssign(complaint.id, Number(e.target.value));
                            }
                          }}
                        >
                          <option value="">
                            {complaint.assigned_authority_id
                              ? "Reassign…"
                              : "Assign…"}
                          </option>
                          {eligibleAuthorities.map((auth) => (
                            <option key={auth.id} value={auth.id}>
                              {auth.name} (#{auth.id})
                            </option>
                          ))}
                        </select>
                        {!eligibleAuthorities.length && (
                          <small
                            className="muted"
                            style={{ display: "block", fontSize: "0.72rem", marginTop: "2px" }}
                          >
                            No active {expectedDept ? titleCase(expectedDept) : "dept"} officer
                          </small>
                        )}
                      </div>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                )}

                <td>
                  <button
                    className="text-button"
                    onClick={() => onHistory(complaint)}
                  >
                    History
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
