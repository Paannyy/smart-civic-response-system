import { useCallback, useEffect, useState } from "react";
import {
  assignComplaint,
  deleteAttachment,
  downloadAttachment,
  getAdminAnalytics,
  getAdminComplaints,
  getAssignedComplaints,
  getComplaintAttachments,
  getComplaintById,
  getComplaintHistory,
  getMyComplaints,
  getNotifications,
  getUsers,
  markAllNotificationsAsRead,
  markNotificationAsRead,
  updateComplaintStatus,
  updateUserStatus,
  uploadAttachment,
} from "../services/api";
import { useAuth } from "../context/AuthContext";
import ComplaintTable from "../components/ComplaintTable";
import StatusBadge from "../components/StatusBadge";
import CreateComplaint from "./CreateComplaint";

const PAGE_SIZE = 20;

const titleCase = (value) =>
  value?.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const formatDuration = (seconds) => {
  if (seconds === null || seconds === undefined) return "N/A (no resolved complaints)";
  if (seconds < 60) return `${Math.round(seconds)} seconds`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} minutes`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} hours`;
  return `${(seconds / 86400).toFixed(1)} days`;
};

function Filters({ filters, setFilters, onSearchChange }) {
  return (
    <div className="filters" style={{ flexWrap: "wrap", alignItems: "center" }}>
      <input
        type="search"
        placeholder="Search complaints by title, description or ID…"
        value={filters.search}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{ flex: "1 1 240px", minWidth: "200px" }}
        aria-label="Search complaints"
      />

      <select
        aria-label="Filter by status"
        value={filters.status}
        onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}
      >
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="assigned">Assigned</option>
        <option value="in_progress">In progress</option>
        <option value="resolved">Resolved</option>
      </select>

      <select
        aria-label="Filter by category"
        value={filters.category}
        onChange={(e) => setFilters({ ...filters, category: e.target.value, page: 1 })}
      >
        <option value="">All categories</option>
        <option value="garbage">Garbage</option>
        <option value="water">Water</option>
        <option value="electricity">Electricity</option>
        <option value="roads">Roads</option>
      </select>

      <select
        aria-label="Filter by priority"
        value={filters.priority}
        onChange={(e) => setFilters({ ...filters, priority: e.target.value, page: 1 })}
      >
        <option value="">All priorities</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
    </div>
  );
}

function Pagination({ page, total, limit, onPageChange, loading }) {
  const totalPages = Math.max(1, Math.ceil(total / limit));

  if (total <= limit && page === 1) {
    return null;
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "14px 18px",
        borderTop: "1px solid #edf1f6",
        fontSize: "0.88rem",
        color: "#667085",
      }}
    >
      <span>
        Showing {total === 0 ? 0 : (page - 1) * limit + 1}–
        {Math.min(page * limit, total)} of {total} items
      </span>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <button
          className="secondary"
          disabled={page <= 1 || loading}
          onClick={() => onPageChange(page - 1)}
          style={{ padding: "6px 12px", fontSize: "0.85rem" }}
        >
          Previous
        </button>
        <span>
          Page {page} of {totalPages}
        </span>
        <button
          className="secondary"
          disabled={page >= totalPages || loading}
          onClick={() => onPageChange(page + 1)}
          style={{ padding: "6px 12px", fontSize: "0.85rem" }}
        >
          Next
        </button>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { token, user, logout } = useAuth();
  const [view, setView] = useState("complaints");
  const [complaints, setComplaints] = useState([]);
  const [totalComplaints, setTotalComplaints] = useState(0);
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [analytics, setAnalytics] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotificationsModal, setShowNotificationsModal] = useState(false);
  const [userPage, setUserPage] = useState(1);
  const [userSearch, setUserSearch] = useState("");
  const [filters, setFilters] = useState({
    status: "",
    category: "",
    priority: "",
    search: "",
    page: 1,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [history, setHistory] = useState(null);
  const [detailComplaint, setDetailComplaint] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [newAttachmentFile, setNewAttachmentFile] = useState(null);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [success, setSuccess] = useState("");

  const loadNotifications = useCallback(async () => {
    try {
      const res = await getNotifications(token, { limit: 30, offset: 0 });
      setNotifications(res.items || []);
      setUnreadCount(res.unread_count ?? 0);
    } catch {
      // Background notifications fetch error gracefully handled
    }
  }, [token]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");

    const offset = (filters.page - 1) * PAGE_SIZE;
    const queryParams = {
      status: filters.status,
      category: filters.category,
      priority: filters.priority,
      search: filters.search,
      limit: PAGE_SIZE,
      offset,
    };

    try {
      loadNotifications();
      if (user.role === "citizen") {
        const res = await getMyComplaints(token, queryParams);
        setComplaints(res.items || []);
        setTotalComplaints(res.total ?? 0);
      } else if (user.role === "authority") {
        const res = await getAssignedComplaints(token, queryParams);
        setComplaints(res.items || []);
        setTotalComplaints(res.total ?? 0);
      } else {
        const userOffset = (userPage - 1) * PAGE_SIZE;
        const [complaintsRes, usersRes, analyticsRes] = await Promise.all([
          getAdminComplaints(token, queryParams),
          getUsers(token, {
            search: userSearch,
            limit: PAGE_SIZE,
            offset: userOffset,
          }),
          getAdminAnalytics(token).catch(() => null),
        ]);
        setComplaints(complaintsRes.items || []);
        setTotalComplaints(complaintsRes.total ?? 0);
        setUsers(usersRes.items || []);
        setTotalUsers(usersRes.total ?? 0);
        if (analyticsRes) {
          setAnalytics(analyticsRes);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filters, loadNotifications, token, user.role, userPage, userSearch]);

  useEffect(() => {
    if (view !== "create") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      load();
    }
  }, [load, view]);

  const handleSearchChange = (searchTerm) => {
    setFilters((prev) => ({
      ...prev,
      search: searchTerm,
      page: 1,
    }));
  };

  const showHistory = async (complaint) => {
    try {
      setHistory({ complaint, entries: null });
      const entries = await getComplaintHistory(complaint.id, token);
      setHistory({ complaint, entries });
    } catch (err) {
      setError(err.message);
      setHistory(null);
    }
  };

  const showDetails = async (complaintId) => {
    try {
      const data = await getComplaintById(complaintId, token);
      setDetailComplaint(data);
      try {
        const attList = await getComplaintAttachments(complaintId, token);
        setAttachments(attList || []);
      } catch {
        setAttachments([]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUploadAttachment = async (e) => {
    e.preventDefault();
    if (!newAttachmentFile || !detailComplaint) return;
    setUploadingAttachment(true);
    try {
      await uploadAttachment(detailComplaint.id, newAttachmentFile, token);
      setNewAttachmentFile(null);
      const attList = await getComplaintAttachments(detailComplaint.id, token);
      setAttachments(attList || []);
      setSuccess("Evidence attachment uploaded successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingAttachment(false);
    }
  };

  const handleDeleteAttachment = async (attId) => {
    if (!window.confirm("Are you sure you want to delete this attachment?")) return;
    try {
      await deleteAttachment(attId, token);
      setAttachments((prev) => prev.filter((a) => a.id !== attId));
      setSuccess("Attachment deleted.");
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMarkRead = async (notifId) => {
    try {
      await markNotificationAsRead(notifId, token);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsAsRead(token);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      setError(err.message);
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await updateComplaintStatus(id, status, token);
      setSuccess(`Complaint #${id} marked ${titleCase(status)}.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const assignAuthority = async (complaintId, authorityId) => {
    try {
      await assignComplaint(complaintId, authorityId, token);
      setSuccess(`Complaint #${complaintId} assigned successfully.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleUser = async (target) => {
    const action = target.is_active ? "deactivate" : "activate";
    if (!window.confirm(`Are you sure you want to ${action} ${target.name}?`)) {
      return;
    }

    try {
      await updateUserStatus(target.id, !target.is_active, token);
      setSuccess(`${target.name} has been ${action}d.`);
      load();
    } catch (err) {
      setError(err.message);
    }
  };

  const citizen = user.role === "citizen";
  const authority = user.role === "authority";
  const admin = user.role === "admin";

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span>SC</span>
          <div>
            Smart Civic <small>Response System</small>
          </div>
        </div>

        <div className="account" style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            className="secondary"
            style={{ position: "relative", padding: "8px 13px", fontSize: "0.85rem" }}
            onClick={() => {
              loadNotifications();
              setShowNotificationsModal(true);
            }}
            aria-label="Notifications"
          >
            🔔 Notifications
            {unreadCount > 0 && (
              <span
                style={{
                  marginLeft: "6px",
                  background: "#dc2626",
                  color: "#fff",
                  borderRadius: "999px",
                  padding: "2px 7px",
                  fontSize: "0.74rem",
                  fontWeight: "750",
                }}
              >
                {unreadCount}
              </span>
            )}
          </button>

          <span>
            {user.name}
            <small>{titleCase(user.role)} portal</small>
          </span>
          <button className="secondary" onClick={() => logout()}>
            Log out
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <p className="eyebrow">PORTAL</p>
          <button
            className={view === "complaints" ? "nav-active" : ""}
            onClick={() => setView("complaints")}
          >
            {authority
              ? "Assigned complaints"
              : admin
              ? "All complaints"
              : "My complaints"}
          </button>

          {citizen && (
            <button
              className={view === "create" ? "nav-active" : ""}
              onClick={() => setView("create")}
            >
              Create complaint
            </button>
          )}

          {admin && (
            <>
              <button
                className={view === "users" ? "nav-active" : ""}
                onClick={() => setView("users")}
              >
                User management
              </button>
              <button
                className={view === "analytics" ? "nav-active" : ""}
                onClick={() => setView("analytics")}
              >
                Analytics
              </button>
            </>
          )}
        </aside>

        <section className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{titleCase(user.role)} WORKSPACE</p>
              <h1>
                {view === "create"
                  ? "Create a complaint"
                  : view === "users"
                  ? "User management"
                  : view === "analytics"
                  ? "Civic Analytics & Metrics"
                  : authority
                  ? "Assigned complaints"
                  : citizen
                  ? "My complaints"
                  : "Civic operations"}
              </h1>
              <p className="muted">
                {view === "analytics"
                  ? "Real-time metrics, turnaround performance, and department distribution."
                  : authority
                  ? "Manage issues assigned to your department."
                  : citizen
                  ? "Track every request you have submitted."
                  : "Review system activity and manage user access."}
              </p>
            </div>

            {view !== "create" && (
              <button className="secondary" onClick={load}>
                Refresh
              </button>
            )}
          </div>

          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          {success && <p className="notice">{success}</p>}

          {view === "create" ? (
            <CreateComplaint
              onCreated={(complaint) => {
                setSuccess(`Complaint #${complaint.id} submitted successfully.`);
                setView("complaints");
              }}
            />
          ) : view === "analytics" ? (
            <div style={{ display: "grid", gap: "22px" }}>
              {analytics ? (
                <>
                  <section className="metrics" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
                    <article>
                      <span>Total Complaints</span>
                      <strong>{analytics.total_complaints}</strong>
                    </article>
                    <article>
                      <span>Pending</span>
                      <strong style={{ color: "#b45309" }}>{analytics.pending_complaints}</strong>
                    </article>
                    <article>
                      <span>Assigned</span>
                      <strong style={{ color: "#0284c7" }}>{analytics.assigned_complaints}</strong>
                    </article>
                    <article>
                      <span>In Progress</span>
                      <strong style={{ color: "#6366f1" }}>{analytics.in_progress_complaints}</strong>
                    </article>
                    <article>
                      <span>Resolved</span>
                      <strong style={{ color: "#15803d" }}>{analytics.resolved_complaints}</strong>
                    </article>
                  </section>

                  <section className="panel" style={{ padding: "24px" }}>
                    <h3 style={{ margin: "0 0 8px" }}>Average Resolution Time</h3>
                    <p className="muted" style={{ marginBottom: "16px" }}>
                      Overall turnaround time from complaint creation to resolution:
                    </p>
                    <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#18745b" }}>
                      {formatDuration(analytics.avg_resolution_time_seconds)}
                    </div>
                  </section>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
                    <section className="panel" style={{ padding: "24px" }}>
                      <h3 style={{ margin: "0 0 16px" }}>Complaints by Category</h3>
                      <div style={{ display: "grid", gap: "14px" }}>
                        {Object.entries(analytics.by_category || {}).map(([cat, count]) => {
                          const pct = analytics.total_complaints > 0
                            ? Math.round((count / analytics.total_complaints) * 100)
                            : 0;
                          return (
                            <div key={cat}>
                              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px", fontSize: "0.88rem" }}>
                                <strong>{titleCase(cat)}</strong>
                                <span>{count} ({pct}%)</span>
                              </div>
                              <div style={{ height: "8px", background: "#edf2f7", borderRadius: "999px", overflow: "hidden" }}>
                                <div
                                  style={{
                                    height: "100%",
                                    width: `${pct}%`,
                                    background: "#18745b",
                                    borderRadius: "999px",
                                    transition: "width 0.3s ease",
                                  }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </section>

                    <section className="panel" style={{ padding: "24px" }}>
                      <h3 style={{ margin: "0 0 16px" }}>Complaints by Department</h3>
                      <div style={{ display: "grid", gap: "14px" }}>
                        {Object.entries(analytics.by_department || {}).map(([dept, count]) => {
                          const avgDept = analytics.avg_resolution_time_by_department?.[dept];
                          return (
                            <div
                              key={dept}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                padding: "10px 14px",
                                background: "#f8fafc",
                                borderRadius: "8px",
                                border: "1px solid #edf2f7",
                              }}
                            >
                              <div>
                                <strong>{titleCase(dept)}</strong>
                                <small className="muted" style={{ display: "block", fontSize: "0.78rem" }}>
                                  Avg: {avgDept > 0 ? formatDuration(avgDept) : "No resolved cases"}
                                </small>
                              </div>
                              <span style={{ fontSize: "1.2rem", fontWeight: "700", color: "#334155" }}>
                                {count}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  </div>
                </>
              ) : (
                <div className="empty-state">
                  <span className="spinner" /> Loading analytics metrics…
                </div>
              )}
            </div>
          ) : view === "users" ? (
            <section className="panel">
              <div
                className="section-heading"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "16px 20px 0",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <h2>Users</h2>
                <input
                  type="search"
                  placeholder="Search users by name or email…"
                  value={userSearch}
                  onChange={(e) => {
                    setUserSearch(e.target.value);
                    setUserPage(1);
                  }}
                  style={{ width: "auto", minWidth: "220px" }}
                  aria-label="Search users"
                />
              </div>

              {loading ? (
                <div className="empty-state">
                  <span className="spinner" /> Loading users…
                </div>
              ) : (
                <>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Email</th>
                          <th>Role</th>
                          <th>Department</th>
                          <th>Status</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.map((target) => (
                          <tr key={target.id}>
                            <td>
                              <strong>{target.name}</strong>
                            </td>
                            <td>{target.email}</td>
                            <td>{titleCase(target.role)}</td>
                            <td>
                              {target.department
                                ? titleCase(target.department)
                                : "—"}
                            </td>
                            <td>
                              <span
                                className={`user-status ${
                                  target.is_active ? "active" : "inactive"
                                }`}
                              >
                                {target.is_active ? "Active" : "Inactive"}
                              </span>
                            </td>
                            <td>
                              <button
                                className="text-button"
                                disabled={target.id === user.id}
                                onClick={() => toggleUser(target)}
                              >
                                {target.is_active ? "Deactivate" : "Activate"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <Pagination
                    page={userPage}
                    total={totalUsers}
                    limit={PAGE_SIZE}
                    onPageChange={setUserPage}
                    loading={loading}
                  />
                </>
              )}
            </section>
          ) : (
            <>
              <section className="metrics">
                <article>
                  <span>Total</span>
                  <strong>{totalComplaints}</strong>
                </article>
                <article>
                  <span>Open</span>
                  <strong>
                    {complaints.filter((item) => item.status !== "resolved").length}
                  </strong>
                </article>
                <article>
                  <span>Resolved</span>
                  <strong>
                    {complaints.filter((item) => item.status === "resolved").length}
                  </strong>
                </article>
              </section>

              <Filters
                filters={filters}
                setFilters={setFilters}
                onSearchChange={handleSearchChange}
              />

              <section className="panel">
                <ComplaintTable
                  complaints={complaints}
                  loading={loading}
                  onHistory={showHistory}
                  onViewDetails={showDetails}
                  onUpdate={authority ? updateStatus : null}
                  onAssign={admin ? assignAuthority : null}
                  authorities={users}
                />

                <Pagination
                  page={filters.page}
                  total={totalComplaints}
                  limit={PAGE_SIZE}
                  onPageChange={(p) => setFilters((prev) => ({ ...prev, page: p }))}
                  loading={loading}
                />
              </section>
            </>
          )}
        </section>
      </div>

      {showNotificationsModal && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Notifications"
            style={{ maxWidth: "600px" }}
          >
            <button
              className="modal-close"
              onClick={() => setShowNotificationsModal(false)}
              aria-label="Close notifications"
            >
              ×
            </button>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div>
                <p className="eyebrow">ACTIVITY ALERTS</p>
                <h2>Notifications ({unreadCount} unread)</h2>
              </div>
              {unreadCount > 0 && (
                <button
                  className="secondary"
                  style={{ fontSize: "0.82rem", padding: "6px 10px" }}
                  onClick={handleMarkAllRead}
                >
                  Mark all read
                </button>
              )}
            </div>

            {notifications.length === 0 ? (
              <div className="empty-state">You have no notifications yet.</div>
            ) : (
              <div style={{ display: "grid", gap: "10px", marginTop: "14px" }}>
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    style={{
                      padding: "14px 16px",
                      borderRadius: "8px",
                      border: notif.is_read ? "1px solid #edf1f6" : "1px solid #bbf7d0",
                      background: notif.is_read ? "#fff" : "#f0fdf4",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "start",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <strong style={{ display: "block", fontSize: "0.92rem", color: notif.is_read ? "#334155" : "#14532d" }}>
                        {notif.title}
                      </strong>
                      <p style={{ margin: "4px 0", fontSize: "0.86rem", color: "#475467" }}>
                        {notif.message}
                      </p>
                      <small className="muted" style={{ fontSize: "0.75rem" }}>
                        {new Date(notif.created_at).toLocaleString()}
                      </small>
                    </div>
                    {!notif.is_read && (
                      <button
                        className="text-button"
                        style={{ fontSize: "0.8rem", whiteSpace: "nowrap" }}
                        onClick={() => handleMarkRead(notif.id)}
                      >
                        Mark read
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      {detailComplaint && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Complaint Details"
            style={{ maxWidth: "650px" }}
          >
            <button
              className="modal-close"
              onClick={() => {
                setDetailComplaint(null);
                setAttachments([]);
                setNewAttachmentFile(null);
              }}
              aria-label="Close details"
            >
              ×
            </button>
            <p className="eyebrow">COMPLAINT #{detailComplaint.id}</p>
            <h2>{detailComplaint.title}</h2>
            <div style={{ marginTop: "12px", display: "grid", gap: "10px" }}>
              <p><strong>Description:</strong> {detailComplaint.description}</p>
              <p><strong>Category:</strong> {titleCase(detailComplaint.category)}</p>
              <p><strong>Priority:</strong> {titleCase(detailComplaint.priority)}</p>
              <p><strong>Status:</strong> <StatusBadge status={detailComplaint.status} /></p>
              <p><strong>Assigned Authority:</strong> {detailComplaint.assigned_authority_id ? `Officer #${detailComplaint.assigned_authority_id}` : "Unassigned"}</p>
              <p className="muted">Submitted on {new Date(detailComplaint.created_at).toLocaleString()}</p>
            </div>

            <hr style={{ margin: "20px 0", border: "0", borderTop: "1px solid #edf1f6" }} />

            <div style={{ display: "grid", gap: "12px" }}>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.1rem" }}>Supporting Evidence & Attachments</h3>
              {attachments.length === 0 ? (
                <p className="muted" style={{ fontSize: "0.88rem" }}>No attachments uploaded for this complaint.</p>
              ) : (
                <div style={{ display: "grid", gap: "8px" }}>
                  {attachments.map((att) => (
                    <div
                      key={att.id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 14px",
                        background: "#f8fafc",
                        borderRadius: "8px",
                        border: "1px solid #e2e8f0",
                        fontSize: "0.88rem",
                      }}
                    >
                      <div>
                        <strong>📎 {att.original_filename}</strong>
                        <small className="muted" style={{ display: "block", fontSize: "0.75rem" }}>
                          {(att.file_size / 1024).toFixed(1)} KB · {new Date(att.created_at).toLocaleDateString()}
                        </small>
                      </div>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          className="secondary"
                          style={{ padding: "4px 10px", fontSize: "0.82rem" }}
                          onClick={() => downloadAttachment(att.id, att.original_filename, token)}
                        >
                          Download
                        </button>
                        {(admin || att.uploaded_by === user.id) && (
                          <button
                            className="text-button"
                            style={{ color: "#dc2626", fontSize: "0.82rem" }}
                            onClick={() => handleDeleteAttachment(att.id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {(admin || detailComplaint.citizen_id === user.id) && (
                <form onSubmit={handleUploadAttachment} style={{ marginTop: "10px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                  <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                    onChange={(e) => setNewAttachmentFile(e.target.files?.[0] || null)}
                    style={{ flex: "1 1 200px" }}
                  />
                  <button
                    className="primary"
                    type="submit"
                    disabled={!newAttachmentFile || uploadingAttachment}
                    style={{ padding: "9px 16px", fontSize: "0.85rem" }}
                  >
                    {uploadingAttachment ? "Uploading…" : "Add Evidence"}
                  </button>
                </form>
              )}
            </div>
          </section>
        </div>
      )}

      {history && (
        <div className="modal-backdrop" role="presentation">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Complaint history"
          >
            <button
              className="modal-close"
              onClick={() => setHistory(null)}
              aria-label="Close history"
            >
              ×
            </button>
            <p className="eyebrow">COMPLAINT #{history.complaint.id}</p>
            <h2>{history.complaint.title}</h2>
            <p className="muted">Status timeline</p>

            {history.entries === null ? (
              <div className="empty-state">
                <span className="spinner" /> Loading history…
              </div>
            ) : history.entries.length ? (
              <ol className="timeline">
                {history.entries.map((entry) => (
                  <li key={entry.id}>
                    <StatusBadge status={entry.status} />
                    <span>
                      {new Date(entry.created_at).toLocaleString()} · Updated by
                      user #{entry.changed_by}
                    </span>
                  </li>
                ))}
              </ol>
            ) : (
              <div className="empty-state">
                No status updates have been recorded yet.
              </div>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
