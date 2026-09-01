import { useState } from "react";
import { createComplaint, uploadAttachment } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function CreateComplaint({ onCreated }) {
  const { token } = useAuth();
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "garbage",
    priority: "medium",
  });
  const [file, setFile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const change = (event) => {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 5 * 1024 * 1024) {
        setError("File size must be under 5MB.");
        setFile(null);
        return;
      }
      setError("");
      setFile(selected);
    }
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const complaint = await createComplaint(form, token);

      if (file) {
        try {
          await uploadAttachment(complaint.id, file, token);
        } catch (uploadErr) {
          console.error("Attachment upload failed:", uploadErr);
        }
      }

      setForm({
        title: "",
        description: "",
        category: "garbage",
        priority: "medium",
      });
      setFile(null);
      onCreated(complaint);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel form-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">NEW REQUEST</p>
          <h2>Report a civic issue</h2>
        </div>
      </div>

      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}

      <form className="complaint-form" onSubmit={submit}>
        <label>
          Issue title
          <input
            name="title"
            value={form.title}
            onChange={change}
            minLength="5"
            maxLength="200"
            placeholder="e.g. Street light is not working"
            required
          />
        </label>

        <label>
          Category
          <select name="category" value={form.category} onChange={change}>
            <option value="garbage">Garbage</option>
            <option value="water">Water</option>
            <option value="electricity">Electricity</option>
            <option value="roads">Roads</option>
          </select>
        </label>

        <label>
          Priority
          <select name="priority" value={form.priority} onChange={change}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>

        <label className="full-width">
          Description
          <textarea
            name="description"
            value={form.description}
            onChange={change}
            minLength="10"
            placeholder="Tell us where the issue is and what needs attention."
            required
          />
        </label>

        <label className="full-width">
          Supporting Evidence (Optional JPG, PNG, PDF &lt; 5MB)
          <input
            type="file"
            accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
            onChange={handleFileChange}
          />
          {file && (
            <small className="muted" style={{ display: "block", marginTop: "4px" }}>
              Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
            </small>
          )}
        </label>

        <div className="full-width actions">
          <button className="primary" disabled={loading}>
            {loading ? "Submitting…" : "Submit complaint"}
          </button>
        </div>
      </form>
    </section>
  );
}
