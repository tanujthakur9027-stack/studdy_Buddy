"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  BookOpen, Plus, Trash, Users, Shield, ClipboardList,
  FileText, Megaphone, Send, BarChart2, Calendar, Download,
  Upload, Edit, ArrowLeft, AlertCircle, X
} from "lucide-react";
import toast from "react-hot-toast";

interface ClassAdminOut {
  id: string;
  admin_user_id: string;
  email: string;
  full_name: string;
  created_at: string;
}

interface SchoolClass {
  id: string;
  name: string;
  section: string;
  academic_year: string;
  display_name: string;
  created_by: string;
  created_at: string;
  is_active: boolean;
  student_count: number;
  admins: ClassAdminOut[];
}

interface StudentEnrollment {
  id: string;
  class_id: string;
  student_id: string;
  roll_number: string;
  full_name: string;
  email: string;
  joined_at: string;
  is_active: boolean;
}

interface Assignment {
  id: string;
  title: string;
  subject_id: string;
  class_id: string;
  due_date: string;
  due_time?: string;
  max_marks: number;
  is_published: boolean;
  created_at: string;
}

interface Note {
  id: string;
  title: string;
  subject: string;
  description: string;
  file_url: string;
  uploader_name: string;
  created_at: string;
}

interface Announcement {
  id: string;
  title: string;
  content: string;
  author_name: string;
  class_id: string | null;
  created_at: string;
}

interface Category {
  id: string;
  name: string;
  class_id?: string | null;
  max_marks: number;
  weightage: number;
}

interface Timetable {
  id: string;
  class_id: string;
  name: string;
  start_time: string;
  periods_per_day: number;
  is_published: boolean;
}

interface BulkUploadResult {
  row: number;
  email: string;
  roll?: string;
  status: "success" | "error";
  error?: string;
}

export default function AdminClassesPage() {
  const { user } = useAuth();
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClass, setSelectedClass] = useState<SchoolClass | null>(null);
  const [activeTab, setActiveTab] = useState<
    "students" | "admins" | "assignments" | "notes" | "announcements" | "broadcast" | "marks" | "timetable"
  >("students");

  // Modals state
  const [showCreateClassModal, setShowCreateClassModal] = useState(false);
  const [createClassForm, setCreateClassForm] = useState({ name: "", section: "A", academic_year: "2024-2025" });
  const [submittingClass, setSubmittingClass] = useState(false);

  // Tab 1: Students
  const [students, setStudents] = useState<StudentEnrollment[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [showAddStudentModal, setShowAddStudentModal] = useState(false);
  const [addStudentForm, setAddStudentForm] = useState({ email: "", full_name: "", roll_number: "", password: "Student@123" });
  const [submittingStudent, setSubmittingStudent] = useState(false);

  // Bulk CSV
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkFile, setBulkFile] = useState<File | null>(null);
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkReport, setBulkReport] = useState<{ succeeded: number; failed: number; results: BulkUploadResult[] } | null>(null);

  // Edit Roll / Transfer Student
  const [editingStudent, setEditingStudent] = useState<StudentEnrollment | null>(null);
  const [editRollForm, setEditRollForm] = useState({ roll_number: "", target_class_id: "" });
  const [savingEditStudent, setSavingEditStudent] = useState(false);

  // Tab 2: Admins
  const [adminAssignForm, setAdminAssignForm] = useState({ email: "", admin_user_id: "" });
  const [assigningAdmin, setAssigningAdmin] = useState(false);

  // Tab 3: Assignments
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [showAssignmentModal, setShowAssignmentModal] = useState(false);
  const [assignmentForm, setAssignmentForm] = useState({
    title: "", subject_id: "General", due_date: "", due_time: "23:59", max_marks: "100", description: "", instructions: ""
  });
  const [assignmentFile, setAssignmentFile] = useState<File | null>(null);
  const [submittingAssignment, setSubmittingAssignment] = useState(false);

  // Tab 4: Notes
  const [notes, setNotes] = useState<Note[]>([]);
  const [showNoteModal, setShowNoteModal] = useState(false);
  const [noteForm, setNoteForm] = useState({ title: "", subject: "General", description: "", visibility: "class" });
  const [noteFile, setNoteFile] = useState<File | null>(null);
  const [submittingNote, setSubmittingNote] = useState(false);

  // Tab 5: Announcements
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [announcementForm, setAnnouncementForm] = useState({ title: "", content: "" });
  const [submittingAnnouncement, setSubmittingAnnouncement] = useState(false);

  // Tab 6: Messages / Broadcast
  const [broadcastForm, setBroadcastForm] = useState({ title: "", message: "", send_email: false });
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([]);
  const [showConfirmBroadcastModal, setShowConfirmBroadcastModal] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);

  // Tab 7: Marks
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [showCatModal, setShowCatModal] = useState(false);
  const [catForm, setCatForm] = useState({ name: "", max_marks: "100", weightage: "100" });
  const [marksInput, setMarksInput] = useState<Record<string, string>>({});
  const [remarksInput, setRemarksInput] = useState<Record<string, string>>({});
  const [savingMarks, setSavingMarks] = useState(false);

  // Tab 8: Timetable
  const [timetables, setTimetables] = useState<Timetable[]>([]);

  const inp = "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-xl text-white text-sm focus:outline-none focus:border-blue-500";

  // Load all accessible classes
  const loadClasses = async () => {
    try {
      setLoading(true);
      const res = await api.get("/api/classes", { withCredentials: true });
      setClasses(res.data);
      if (selectedClass) {
        const refreshed = res.data.find((c: SchoolClass) => c.id === selectedClass.id);
        if (refreshed) setSelectedClass(refreshed);
      }
    } catch {
      toast.error("Failed to load classes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClasses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When selectedClass changes, reload its tab data
  useEffect(() => {
    if (!selectedClass) return;
    loadStudents(selectedClass.id);
    if (activeTab === "assignments") loadAssignments(selectedClass.id);
    if (activeTab === "notes") loadNotes(selectedClass.id);
    if (activeTab === "announcements") loadAnnouncements(selectedClass.id);
    if (activeTab === "marks") loadCategories(selectedClass.id);
    if (activeTab === "timetable") loadTimetables(selectedClass.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClass?.id, activeTab]);

  const loadStudents = async (classId: string) => {
    try {
      setLoadingStudents(true);
      const res = await api.get(`/api/classes/${classId}/students`, { withCredentials: true });
      setStudents(res.data);
      // Default broadcast targets to all
      setSelectedStudentIds(res.data.map((s: StudentEnrollment) => s.student_id));
    } catch {
      toast.error("Failed to load class roster");
    } finally {
      setLoadingStudents(false);
    }
  };

  const loadAssignments = async (classId: string) => {
    try {
      const res = await api.get(`/api/admin/assignments?class_id=${classId}`, { withCredentials: true });
      setAssignments(res.data);
    } catch { /* ignore */ }
  };

  const loadNotes = async (classId: string) => {
    try {
      const res = await api.get(`/api/notes?class_id=${classId}`, { withCredentials: true });
      setNotes(res.data);
    } catch { /* ignore */ }
  };

  const loadAnnouncements = async (classId: string) => {
    try {
      const res = await api.get(`/api/admin/announcements?class_id=${classId}`, { withCredentials: true });
      setAnnouncements(res.data);
    } catch { /* ignore */ }
  };

  const loadCategories = async (classId: string) => {
    try {
      const res = await api.get(`/api/admin/assessment-categories?class_id=${classId}`, { withCredentials: true });
      setCategories(res.data);
      if (res.data.length > 0 && !selectedCategory) {
        setSelectedCategory(res.data[0]);
      }
    } catch { /* ignore */ }
  };

  const loadTimetables = async (classId: string) => {
    try {
      const res = await api.get(`/api/admin/timetables?class_id=${classId}`, { withCredentials: true });
      setTimetables(res.data);
    } catch { /* ignore */ }
  };

  // ── Class Actions ──────────────────────────────────────────────────────────
  const handleCreateClass = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingClass(true);
    try {
      const res = await api.post("/api/classes", createClassForm, { withCredentials: true });
      setClasses(prev => [...prev, res.data]);
      setShowCreateClassModal(false);
      setCreateClassForm({ name: "", section: "A", academic_year: "2024-2025" });
      toast.success(`Class ${res.data.display_name} created successfully!`);
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create class");
    } finally {
      setSubmittingClass(false);
    }
  };

  const handleArchiveClass = async (cls: SchoolClass) => {
    if (!confirm(`Are you sure you want to archive class ${cls.display_name}?`)) return;
    try {
      await api.delete(`/api/classes/${cls.id}`, { withCredentials: true });
      toast.success(`Class ${cls.display_name} archived`);
      if (selectedClass?.id === cls.id) setSelectedClass(null);
      loadClasses();
    } catch {
      toast.error("Failed to archive class");
    }
  };

  // ── Tab 1: Student Actions ──────────────────────────────────────────────────
  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass) return;
    setSubmittingStudent(true);
    try {
      const res = await api.post(`/api/classes/${selectedClass.id}/students`, addStudentForm, { withCredentials: true });
      setStudents(prev => [...prev, res.data]);
      setShowAddStudentModal(false);
      setAddStudentForm({ email: "", full_name: "", roll_number: "", password: "Student@123" });
      toast.success("Student added to class!");
      loadClasses();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to add student");
    } finally {
      setSubmittingStudent(false);
    }
  };

  const handleDownloadTemplate = () => {
    const csvContent = "name,email,roll_number,password\nJohn Doe,john@school.edu,10A-01,Student@123\nJane Smith,jane@school.edu,10A-02,Student@123\n";
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `class_students_template.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleBulkUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass || !bulkFile) {
      toast.error("Please choose a CSV file first");
      return;
    }
    setBulkUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", bulkFile);
      const res = await api.post(`/api/classes/${selectedClass.id}/students/bulk`, fd, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      setBulkReport(res.data);
      toast.success(`Processed: ${res.data.succeeded} added, ${res.data.failed} failed`);
      loadStudents(selectedClass.id);
      loadClasses();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Bulk import failed");
    } finally {
      setBulkUploading(false);
    }
  };

  const handleSaveEditStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass || !editingStudent) return;
    setSavingEditStudent(true);
    try {
      await api.put(
        `/api/classes/${selectedClass.id}/students/${editingStudent.student_id}`,
        {
          roll_number: editRollForm.roll_number || undefined,
          target_class_id: editRollForm.target_class_id || undefined,
        },
        { withCredentials: true }
      );
      toast.success("Student updated successfully!");
      setEditingStudent(null);
      loadStudents(selectedClass.id);
      loadClasses();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to update student");
    } finally {
      setSavingEditStudent(false);
    }
  };

  const handleRemoveStudent = async (studentId: string, name: string) => {
    if (!selectedClass) return;
    if (!confirm(`Remove ${name} from class ${selectedClass.display_name}? (Academic records will be preserved)`)) return;
    try {
      await api.delete(`/api/classes/${selectedClass.id}/students/${studentId}`, { withCredentials: true });
      toast.success("Student removed from class");
      setStudents(prev => prev.filter(s => s.student_id !== studentId));
      loadClasses();
    } catch {
      toast.error("Failed to remove student");
    }
  };

  // ── Tab 2: Admin Actions ───────────────────────────────────────────────────
  const handleAssignAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass) return;
    setAssigningAdmin(true);
    try {
      const res = await api.post(`/api/classes/${selectedClass.id}/admins`, adminAssignForm, { withCredentials: true });
      setSelectedClass(res.data);
      setAdminAssignForm({ email: "", admin_user_id: "" });
      toast.success("Class Admin assigned successfully!");
      loadClasses();
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to assign admin");
    } finally {
      setAssigningAdmin(false);
    }
  };

  const handleRemoveAdmin = async (adminUserId: string, name: string) => {
    if (!selectedClass) return;
    if (!confirm(`Unassign ${name} as administrator of ${selectedClass.display_name}?`)) return;
    try {
      await api.delete(`/api/classes/${selectedClass.id}/admins/${adminUserId}`, { withCredentials: true });
      toast.success("Admin unassigned");
      loadClasses();
      setSelectedClass(prev => prev ? { ...prev, admins: prev.admins.filter(a => a.admin_user_id !== adminUserId) } : null);
    } catch {
      toast.error("Failed to unassign admin");
    }
  };

  // ── Tab 3: Assignment Actions ──────────────────────────────────────────────
  const handleCreateAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass) return;
    setSubmittingAssignment(true);
    try {
      const fd = new FormData();
      fd.append("title", assignmentForm.title);
      fd.append("subject_id", assignmentForm.subject_id || "General");
      fd.append("class_id", selectedClass.id);
      fd.append("due_date", assignmentForm.due_date);
      fd.append("due_time", assignmentForm.due_time || "23:59");
      fd.append("max_marks", assignmentForm.max_marks || "100");
      if (assignmentForm.description) fd.append("description", assignmentForm.description);
      if (assignmentForm.instructions) fd.append("instructions", assignmentForm.instructions);
      if (assignmentFile) fd.append("file", assignmentFile);

      const res = await api.post("/api/admin/assignments", fd, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      setAssignments(prev => [res.data, ...prev]);
      setShowAssignmentModal(false);
      setAssignmentForm({ title: "", subject_id: "General", due_date: "", due_time: "23:59", max_marks: "100", description: "", instructions: "" });
      setAssignmentFile(null);
      toast.success("Assignment created for this class!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create assignment");
    } finally {
      setSubmittingAssignment(false);
    }
  };

  const handlePublishAssignment = async (id: string) => {
    try {
      await api.post(`/api/admin/assignments/${id}/publish`, {}, { withCredentials: true });
      setAssignments(prev => prev.map(a => a.id === id ? { ...a, is_published: true } : a));
      toast.success("Assignment published!");
    } catch {
      toast.error("Failed to publish");
    }
  };

  const handleDeleteAssignment = async (id: string) => {
    if (!confirm("Delete this assignment?")) return;
    try {
      await api.delete(`/api/admin/assignments/${id}`, { withCredentials: true });
      setAssignments(prev => prev.filter(a => a.id !== id));
      toast.success("Assignment deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  // ── Tab 4: Note Actions ────────────────────────────────────────────────────
  const handleUploadNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass || !noteFile) {
      toast.error("Please select a file to upload");
      return;
    }
    setSubmittingNote(true);
    try {
      const fd = new FormData();
      fd.append("title", noteForm.title);
      fd.append("subject", noteForm.subject || "General");
      fd.append("description", noteForm.description || "");
      fd.append("visibility", "class");
      fd.append("class_id", selectedClass.id);
      fd.append("file", noteFile);

      const res = await api.post("/api/notes", fd, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" },
      });
      setNotes(prev => [res.data, ...prev]);
      setShowNoteModal(false);
      setNoteForm({ title: "", subject: "General", description: "", visibility: "class" });
      setNoteFile(null);
      toast.success("Note shared with this class!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to upload note");
    } finally {
      setSubmittingNote(false);
    }
  };

  // ── Tab 5: Announcement Actions ────────────────────────────────────────────
  const handleCreateAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass) return;
    setSubmittingAnnouncement(true);
    try {
      const res = await api.post(
        "/api/admin/announcements",
        { title: announcementForm.title, content: announcementForm.content, class_id: selectedClass.id },
        { withCredentials: true }
      );
      setAnnouncements(prev => [res.data, ...prev]);
      setShowAnnouncementModal(false);
      setAnnouncementForm({ title: "", content: "" });
      toast.success("Class announcement posted!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to post announcement");
    } finally {
      setSubmittingAnnouncement(false);
    }
  };

  const handleDeleteAnnouncement = async (id: string) => {
    if (!confirm("Delete this announcement?")) return;
    try {
      await api.delete(`/api/admin/announcements/${id}`, { withCredentials: true });
      setAnnouncements(prev => prev.filter(a => a.id !== id));
      toast.success("Announcement deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  // ── Tab 6: Broadcast Actions ───────────────────────────────────────────────
  const toggleStudentSelection = (studentId: string) => {
    setSelectedStudentIds(prev =>
      prev.includes(studentId) ? prev.filter(id => id !== studentId) : [...prev, studentId]
    );
  };

  const toggleSelectAllStudents = () => {
    if (selectedStudentIds.length === students.length) {
      setSelectedStudentIds([]);
    } else {
      setSelectedStudentIds(students.map(s => s.student_id));
    }
  };

  const handleBroadcastSubmit = async () => {
    if (!selectedClass) return;
    setBroadcasting(true);
    try {
      const isNarrowed = selectedStudentIds.length > 0 && selectedStudentIds.length < students.length;
      const res = await api.post(
        `/api/classes/${selectedClass.id}/broadcast`,
        {
          title: broadcastForm.title,
          message: broadcastForm.message,
          send_email: broadcastForm.send_email,
          target_student_ids: isNarrowed ? selectedStudentIds : null,
        },
        { withCredentials: true }
      );
      toast.success(`Broadcast sent to ${res.data.recipient_count} students!`);
      setShowConfirmBroadcastModal(false);
      setBroadcastForm({ title: "", message: "", send_email: false });
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Broadcast failed");
    } finally {
      setBroadcasting(false);
    }
  };

  // ── Tab 7: Marks Actions ───────────────────────────────────────────────────
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedClass) return;
    try {
      const res = await api.post(
        "/api/admin/assessment-categories",
        {
          name: catForm.name,
          class_id: selectedClass.id,
          max_marks: parseFloat(catForm.max_marks),
          weightage: parseFloat(catForm.weightage),
        },
        { withCredentials: true }
      );
      setCategories(prev => [...prev, res.data]);
      setSelectedCategory(res.data);
      setShowCatModal(false);
      setCatForm({ name: "", max_marks: "100", weightage: "100" });
      toast.success("Category created!");
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to create category");
    }
  };

  const handleSaveMarks = async () => {
    if (!selectedClass || !selectedCategory) {
      toast.error("Please select an assessment category first");
      return;
    }
    const entries = students
      .filter(s => marksInput[s.student_id] !== undefined && marksInput[s.student_id] !== "")
      .map(s => ({
        student_id: s.student_id,
        category_id: selectedCategory.id,
        class_id: selectedClass.id,
        obtained_marks: parseFloat(marksInput[s.student_id]),
        remarks: remarksInput[s.student_id] || "",
      }));

    if (entries.length === 0) {
      toast.error("Please enter marks for at least one student");
      return;
    }

    setSavingMarks(true);
    try {
      await api.post("/api/admin/marks", entries, { withCredentials: true });
      toast.success(`Saved marks for ${entries.length} students!`);
    } catch (err: unknown) {
      toast.error((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Failed to save marks");
    } finally {
      setSavingMarks(false);
    }
  };

  const handlePublishMarks = async () => {
    if (!selectedCategory) return;
    if (!confirm(`Publish all marks for "${selectedCategory.name}"? Enrolled students will receive notifications.`)) return;
    try {
      await api.post("/api/admin/marks/publish", { category_id: selectedCategory.id }, { withCredentials: true });
      toast.success("Marks published to students!");
    } catch {
      toast.error("Failed to publish marks");
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // VIEW: Class Detail Workspace (when a class is selected)
  // ─────────────────────────────────────────────────────────────────────────────
  if (selectedClass) {
    const isSuperAdmin = Boolean(user?.is_super_admin);
    const broadcastRecipientCount =
      selectedStudentIds.length === 0 || selectedStudentIds.length === students.length
        ? students.length
        : selectedStudentIds.length;

    return (
      <div className="space-y-6">
        {/* Detail Header */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSelectedClass(null)}
                className="p-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-xl transition-colors flex items-center gap-1.5 text-sm"
              >
                <ArrowLeft className="w-4 h-4" /> All Classes
              </button>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Class {selectedClass.display_name}
                  </h1>
                  <span className="text-xs bg-blue-500/20 text-blue-400 font-medium px-2.5 py-0.5 rounded-full">
                    {selectedClass.academic_year}
                  </span>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                    selectedClass.is_active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                  }`}>
                    {selectedClass.is_active ? "Active" : "Archived"}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Enrolled Students: <span className="text-white font-semibold">{students.length}</span> •
                  Class Admins: <span className="text-white font-semibold">
                    {selectedClass.admins?.map(a => a.full_name || a.email).join(", ") || "None assigned"}
                  </span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleArchiveClass(selectedClass)}
                className="p-2 text-gray-500 hover:text-red-400 bg-gray-800 hover:bg-gray-800/80 rounded-xl transition-colors text-xs flex items-center gap-1"
                title="Archive Class"
              >
                <Trash className="w-4 h-4" /> Archive
              </button>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex gap-2 overflow-x-auto mt-6 pt-4 border-t border-gray-800">
            {[
              { id: "students", label: "Students", count: students.length, icon: Users },
              { id: "admins", label: "Class Admins", count: selectedClass.admins?.length || 0, icon: Shield },
              { id: "assignments", label: "Assignments", count: assignments.length, icon: ClipboardList },
              { id: "notes", label: "Notes", count: notes.length, icon: FileText },
              { id: "announcements", label: "Announcements", count: announcements.length, icon: Megaphone },
              { id: "broadcast", label: "Broadcast", count: null, icon: Send },
              { id: "marks", label: "Marks", count: null, icon: BarChart2 },
              { id: "timetable", label: "Timetable", count: null, icon: Calendar },
            ].map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                    isActive
                      ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                      : "bg-gray-800/60 text-gray-400 hover:text-white hover:bg-gray-800"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                  {tab.count !== null && (
                    <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isActive ? "bg-white/20 text-white" : "bg-gray-700 text-gray-300"
                    }`}>
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Tab 1: Students ──────────────────────────────────────────────── */}
        {activeTab === "students" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-bold text-white">Student Roster</h2>
                <span className="text-xs bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">
                  {students.length} enrolled
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={handleDownloadTemplate}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs rounded-xl transition-colors"
                >
                  <Download className="w-3.5 h-3.5" /> CSV Template
                </button>
                <button
                  onClick={() => setShowBulkModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-xl transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" /> Bulk CSV Upload
                </button>
                <button
                  onClick={() => setShowAddStudentModal(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-xl transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Add Student
                </button>
              </div>
            </div>

            {loadingStudents ? (
              <div className="p-12 text-center text-gray-500">Loading student roster...</div>
            ) : students.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
                <Users className="w-12 h-12 text-gray-700 mx-auto mb-3" />
                <p className="text-gray-400 text-sm">No students enrolled in this class yet.</p>
                <p className="text-xs text-gray-600 mt-1">Use &quot;Add Student&quot; or upload a CSV to build the roster.</p>
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
                      <tr>
                        <th className="px-5 py-3">Roll No</th>
                        <th className="px-5 py-3">Full Name</th>
                        <th className="px-5 py-3">Email Address</th>
                        <th className="px-5 py-3">Joined Date</th>
                        <th className="px-5 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 text-gray-300">
                      {students.map(s => (
                        <tr key={s.id} className="hover:bg-gray-800/30 transition-colors">
                          <td className="px-5 py-3.5 font-mono text-blue-400 font-semibold">{s.roll_number}</td>
                          <td className="px-5 py-3.5 text-white font-medium">{s.full_name}</td>
                          <td className="px-5 py-3.5 text-gray-400">{s.email}</td>
                          <td className="px-5 py-3.5 text-xs text-gray-500">
                            {new Date(s.joined_at).toLocaleDateString()}
                          </td>
                          <td className="px-5 py-3.5 text-right space-x-2">
                            <button
                              onClick={() => {
                                setEditingStudent(s);
                                setEditRollForm({ roll_number: s.roll_number, target_class_id: "" });
                              }}
                              className="px-2.5 py-1 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg transition-colors inline-flex items-center gap-1"
                            >
                              <Edit className="w-3 h-3" /> Edit / Transfer
                            </button>
                            <button
                              onClick={() => handleRemoveStudent(s.student_id, s.full_name)}
                              className="p-1 text-gray-500 hover:text-red-400 rounded-lg transition-colors inline-flex items-center"
                              title="Remove from class"
                            >
                              <Trash className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Tab 2: Class Admins ───────────────────────────────────────────── */}
        {activeTab === "admins" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Shield className="w-5 h-5 text-indigo-400" /> Assigned Class Administrators
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Class admins can manage roster, assignments, notes, marks, and announcements for this class.
                </p>
              </div>
            </div>

            {isSuperAdmin ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 mb-4">
                <h3 className="text-xs font-semibold uppercase text-indigo-400 tracking-wider mb-3">
                  Assign New Admin to {selectedClass.display_name}
                </h3>
                <form onSubmit={handleAssignAdmin} className="flex flex-wrap gap-3 items-end">
                  <div className="flex-1 min-w-[240px]">
                    <label className="text-xs text-gray-400 block mb-1">Admin Email Address</label>
                    <input
                      required
                      placeholder="admin@school.edu"
                      value={adminAssignForm.email}
                      onChange={e => setAdminAssignForm(f => ({ ...f, email: e.target.value }))}
                      className={inp}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={assigningAdmin}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {assigningAdmin ? "Assigning..." : "Assign Admin"}
                  </button>
                </form>
              </div>
            ) : (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-4 text-xs text-blue-300">
                Notice: Only Super Administrators can assign or reassign class administrator permissions.
              </div>
            )}

            {selectedClass.admins.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 text-center text-gray-400 text-sm">
                No dedicated class admins assigned. Super Admins retain global access.
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden divide-y divide-gray-800">
                {selectedClass.admins.map(adm => (
                  <div key={adm.id} className="p-4 flex items-center justify-between hover:bg-gray-800/20">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-indigo-600/30 text-indigo-400 flex items-center justify-center font-bold text-xs">
                        {adm.full_name?.charAt(0) || "A"}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-white">{adm.full_name || "Admin User"}</p>
                        <p className="text-xs text-gray-400">{adm.email}</p>
                      </div>
                    </div>
                    {isSuperAdmin && (
                      <button
                        onClick={() => handleRemoveAdmin(adm.admin_user_id, adm.full_name || adm.email)}
                        className="p-1.5 text-gray-500 hover:text-red-400 transition-colors"
                        title="Remove admin assignment"
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab 3: Assignments ───────────────────────────────────────────── */}
        {activeTab === "assignments" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-purple-400" /> Class Assignments
              </h2>
              <button
                onClick={() => setShowAssignmentModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-xl"
              >
                <Plus className="w-4 h-4" /> New Assignment for {selectedClass.display_name}
              </button>
            </div>

            {assignments.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                No assignments created for {selectedClass.display_name} yet.
              </div>
            ) : (
              <div className="space-y-3">
                {assignments.map(a => (
                  <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-white text-base">{a.title}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          a.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"
                        }`}>
                          {a.is_published ? "Published" : "Draft"}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        Due: <span className="text-white">{a.due_date} {a.due_time}</span> • Max Marks: {a.max_marks}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {!a.is_published && (
                        <button
                          onClick={() => handlePublishAssignment(a.id)}
                          className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg"
                        >
                          Publish to Class
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteAssignment(a.id)}
                        className="p-1.5 text-gray-500 hover:text-red-400"
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab 4: Notes ─────────────────────────────────────────────────── */}
        {activeTab === "notes" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-emerald-400" /> Class Study Materials & Notes
              </h2>
              <button
                onClick={() => setShowNoteModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl"
              >
                <Plus className="w-4 h-4" /> Upload Note for {selectedClass.display_name}
              </button>
            </div>

            {notes.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                No notes shared with this class yet.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {notes.map(n => (
                  <div key={n.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between">
                        <h4 className="font-semibold text-white text-sm">{n.title}</h4>
                        <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full">
                          {n.subject}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 mt-2 line-clamp-2">{n.description || "No description provided."}</p>
                    </div>
                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-800 text-xs">
                      <span className="text-gray-500">By {n.uploader_name}</span>
                      <a
                        href={n.file_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1"
                      >
                        <Download className="w-3.5 h-3.5" /> Download
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab 5: Announcements ─────────────────────────────────────────── */}
        {activeTab === "announcements" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Megaphone className="w-5 h-5 text-orange-400" /> Class Announcements
              </h2>
              <button
                onClick={() => setShowAnnouncementModal(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-orange-600 hover:bg-orange-700 text-white text-xs font-semibold rounded-xl"
              >
                <Plus className="w-4 h-4" /> Post Announcement
              </button>
            </div>

            {announcements.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                No announcements for {selectedClass.display_name} yet.
              </div>
            ) : (
              <div className="space-y-3">
                {announcements.map(ann => (
                  <div key={ann.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-white text-base">{ann.title}</h3>
                        <p className="text-xs text-gray-500 mt-0.5">
                          By {ann.author_name} • {new Date(ann.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <button
                        onClick={() => handleDeleteAnnouncement(ann.id)}
                        className="p-1.5 text-gray-500 hover:text-red-400"
                      >
                        <Trash className="w-4 h-4" />
                      </button>
                    </div>
                    <p className="text-sm text-gray-300 mt-3 whitespace-pre-wrap">{ann.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Tab 6: Messages / Broadcast ──────────────────────────────────── */}
        {activeTab === "broadcast" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Compose Form */}
            <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Send className="w-5 h-5 text-blue-400" /> Send Class Broadcast
              </h2>
              <p className="text-xs text-gray-400">
                Dispatches high-priority in-app notification and optional email to students in {selectedClass.display_name}.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Subject / Title *</label>
                  <input
                    required
                    placeholder="e.g. Schedule change for Tuesday"
                    value={broadcastForm.title}
                    onChange={e => setBroadcastForm(f => ({ ...f, title: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Message Content *</label>
                  <textarea
                    required
                    rows={6}
                    placeholder="Type your message here..."
                    value={broadcastForm.message}
                    onChange={e => setBroadcastForm(f => ({ ...f, message: e.target.value }))}
                    className={inp}
                  />
                </div>
                <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-300">
                  <input
                    type="checkbox"
                    checked={broadcastForm.send_email}
                    onChange={e => setBroadcastForm(f => ({ ...f, send_email: e.target.checked }))}
                    className="rounded bg-gray-800 border-gray-700 text-blue-600 focus:ring-0"
                  />
                  Also send via Email notification to recipients
                </label>
              </div>

              {/* Real-time recipient preview badge */}
              <div className="bg-gray-800/60 rounded-xl p-3 flex items-center justify-between text-xs">
                <span className="text-gray-400">Recipient Audience:</span>
                <span className="text-blue-400 font-semibold">
                  Sending to: {selectedClass.display_name} ({broadcastRecipientCount} of {students.length} students)
                </span>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  disabled={!broadcastForm.title.trim() || !broadcastForm.message.trim() || broadcastRecipientCount === 0}
                  onClick={() => setShowConfirmBroadcastModal(true)}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white text-xs font-semibold rounded-xl flex items-center gap-2"
                >
                  <Send className="w-4 h-4" /> Send Broadcast
                </button>
              </div>
            </div>

            {/* Recipient Filter / Narrowing Column */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
                  Target Specific Students
                </h3>
                <button
                  onClick={toggleSelectAllStudents}
                  className="text-xs text-blue-400 hover:text-blue-300 font-medium"
                >
                  {selectedStudentIds.length === students.length ? "Deselect All" : "Select All"}
                </button>
              </div>
              <p className="text-[11px] text-gray-500">
                Uncheck any students you wish to exclude from this message.
              </p>

              <div className="max-h-[360px] overflow-y-auto space-y-1.5 pr-1">
                {students.map(s => {
                  const isChecked = selectedStudentIds.includes(s.student_id);
                  return (
                    <label
                      key={s.student_id}
                      className={`flex items-center justify-between p-2 rounded-xl text-xs cursor-pointer transition-colors ${
                        isChecked ? "bg-gray-800 text-white" : "bg-gray-800/30 text-gray-500 hover:bg-gray-800/50"
                      }`}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleStudentSelection(s.student_id)}
                          className="rounded bg-gray-700 border-gray-600 text-blue-600 focus:ring-0"
                        />
                        <span className="truncate">{s.full_name}</span>
                      </div>
                      <span className="font-mono text-[10px] text-gray-400 ml-2">{s.roll_number}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ── Tab 7: Marks ─────────────────────────────────────────────────── */}
        {activeTab === "marks" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <BarChart2 className="w-5 h-5 text-yellow-400" /> Enter & Publish Marks
                </h2>
                <p className="text-xs text-gray-400 mt-0.5">
                  Record exam or assignment marks for students of {selectedClass.display_name}.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowCatModal(true)}
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-white text-xs rounded-xl"
                >
                  <Plus className="w-3.5 h-3.5 inline mr-1" /> New Category
                </button>
                <button
                  onClick={handlePublishMarks}
                  disabled={!selectedCategory}
                  className="px-3.5 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-40 text-white text-xs font-semibold rounded-xl"
                >
                  Publish Marks
                </button>
              </div>
            </div>

            {/* Category Selector */}
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-4 flex flex-wrap items-center gap-3">
              <label className="text-xs text-gray-400">Select Category:</label>
              <select
                value={selectedCategory?.id || ""}
                onChange={e => {
                  const cat = categories.find(c => c.id === e.target.value) || null;
                  setSelectedCategory(cat);
                }}
                className={`${inp} max-w-xs`}
              >
                <option value="">Choose an Assessment Category...</option>
                {categories.map(c => (
                  <option key={c.id} value={c.id}>
                    {c.name} (Max: {c.max_marks})
                  </option>
                ))}
              </select>
              {selectedCategory && (
                <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-lg">
                  Max Marks: {selectedCategory.max_marks} • Weightage: {selectedCategory.weightage}%
                </span>
              )}
            </div>

            {/* Marks Entry Grid */}
            {students.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                No students enrolled in this class to grade.
              </div>
            ) : !selectedCategory ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                Please select or create an assessment category above to enter marks.
              </div>
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-gray-800/50 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-800">
                      <tr>
                        <th className="px-5 py-3">Roll No</th>
                        <th className="px-5 py-3">Student Name</th>
                        <th className="px-5 py-3">Obtained Marks (Max {selectedCategory.max_marks})</th>
                        <th className="px-5 py-3">Remarks</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800 text-gray-300">
                      {students.map(s => (
                        <tr key={s.id} className="hover:bg-gray-800/20">
                          <td className="px-5 py-2.5 font-mono text-blue-400">{s.roll_number}</td>
                          <td className="px-5 py-2.5 text-white font-medium">{s.full_name}</td>
                          <td className="px-5 py-2.5">
                            <input
                              type="number"
                              min="0"
                              max={selectedCategory.max_marks}
                              step="0.5"
                              placeholder="0"
                              value={marksInput[s.student_id] ?? ""}
                              onChange={e => setMarksInput(prev => ({ ...prev, [s.student_id]: e.target.value }))}
                              className="w-28 px-2.5 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                            />
                          </td>
                          <td className="px-5 py-2.5">
                            <input
                              placeholder="Optional remarks..."
                              value={remarksInput[s.student_id] ?? ""}
                              onChange={e => setRemarksInput(prev => ({ ...prev, [s.student_id]: e.target.value }))}
                              className="w-full max-w-sm px-2.5 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="p-4 bg-gray-800/40 border-t border-gray-800 flex justify-end">
                  <button
                    onClick={handleSaveMarks}
                    disabled={savingMarks}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {savingMarks ? "Saving..." : "Save Marks"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Tab 8: Timetable ─────────────────────────────────────────────── */}
        {activeTab === "timetable" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Calendar className="w-5 h-5 text-blue-400" /> Class Schedule & Timetable
              </h2>
              <a
                href="/admin/timetable"
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl"
              >
                Open Full Timetable Editor
              </a>
            </div>

            {timetables.length === 0 ? (
              <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center text-gray-400 text-sm">
                No active timetable configured specifically for {selectedClass.display_name}.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {timetables.map(tt => (
                  <div key={tt.id} className="bg-gray-900 border border-gray-800 rounded-2xl p-5">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-white">{tt.name}</h4>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        tt.is_published ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"
                      }`}>
                        {tt.is_published ? "Published" : "Draft"}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                      Starts at {tt.start_time} • {tt.periods_per_day} periods / day
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── Modals for Class Detail ───────────────────────────────────────── */}

        {/* Add Student Modal */}
        {showAddStudentModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Add Student to {selectedClass.display_name}</h3>
                <button onClick={() => setShowAddStudentModal(false)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleAddStudent} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Student Full Name *</label>
                  <input
                    required
                    placeholder="e.g. John Doe"
                    value={addStudentForm.full_name}
                    onChange={e => setAddStudentForm(f => ({ ...f, full_name: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Email Address *</label>
                  <input
                    required
                    type="email"
                    placeholder="john@school.edu"
                    value={addStudentForm.email}
                    onChange={e => setAddStudentForm(f => ({ ...f, email: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Roll Number (Unique to Class) *</label>
                  <input
                    required
                    placeholder="e.g. 10A-01"
                    value={addStudentForm.roll_number}
                    onChange={e => setAddStudentForm(f => ({ ...f, roll_number: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Default Password</label>
                  <input
                    required
                    type="password"
                    placeholder="Student@123"
                    value={addStudentForm.password}
                    onChange={e => setAddStudentForm(f => ({ ...f, password: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddStudentModal(false)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingStudent}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {submittingStudent ? "Adding..." : "Add to Class"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Bulk CSV Upload Modal */}
        {showBulkModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Bulk CSV Upload — {selectedClass.display_name}</h3>
                <button onClick={() => { setShowBulkModal(false); setBulkReport(null); setBulkFile(null); }} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {!bulkReport ? (
                <form onSubmit={handleBulkUpload} className="space-y-4">
                  <p className="text-xs text-gray-400">
                    Upload a CSV file containing columns: <code className="text-blue-400">name, email, roll_number, password</code>.
                    Roll numbers must be unique within {selectedClass.display_name}.
                  </p>
                  <div className="border-2 border-dashed border-gray-700 rounded-2xl p-6 text-center">
                    <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                    <input
                      type="file"
                      accept=".csv"
                      onChange={e => setBulkFile(e.target.files?.[0] || null)}
                      className="text-xs text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white"
                    />
                    {bulkFile && (
                      <p className="text-xs text-green-400 mt-2">Selected: {bulkFile.name}</p>
                    )}
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <button
                      type="button"
                      onClick={handleDownloadTemplate}
                      className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                    >
                      <Download className="w-3.5 h-3.5" /> Download Template
                    </button>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setShowBulkModal(false)}
                        className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        disabled={bulkUploading || !bulkFile}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                      >
                        {bulkUploading ? "Processing..." : "Upload & Enroll"}
                      </button>
                    </div>
                  </div>
                </form>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-bold text-green-400">{bulkReport.succeeded}</p>
                      <p className="text-xs text-gray-400">Successfully Enrolled</p>
                    </div>
                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-center">
                      <p className="text-2xl font-bold text-red-400">{bulkReport.failed}</p>
                      <p className="text-xs text-gray-400">Errors Encountered</p>
                    </div>
                  </div>

                  <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Per-Row Report</h4>
                  <div className="max-h-60 overflow-y-auto divide-y divide-gray-800 border border-gray-800 rounded-xl">
                    {bulkReport.results.map((r, i) => (
                      <div key={i} className="p-2.5 text-xs flex items-center justify-between">
                        <div>
                          <span className="text-gray-500 font-mono mr-2">Row {r.row}</span>
                          <span className="text-white font-medium">{r.email}</span>
                          {r.error && <p className="text-red-400 text-[11px] mt-0.5">{r.error}</p>}
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                          r.status === "success" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                        }`}>
                          {r.status}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      onClick={() => { setShowBulkModal(false); setBulkReport(null); setBulkFile(null); }}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl"
                    >
                      Done
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Edit Roll / Transfer Student Modal */}
        {editingStudent && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Edit Student — {editingStudent.full_name}</h3>
                <button onClick={() => setEditingStudent(null)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSaveEditStudent} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Roll Number</label>
                  <input
                    value={editRollForm.roll_number}
                    onChange={e => setEditRollForm(f => ({ ...f, roll_number: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Transfer to Another Class</label>
                  <select
                    value={editRollForm.target_class_id}
                    onChange={e => setEditRollForm(f => ({ ...f, target_class_id: e.target.value }))}
                    className={inp}
                  >
                    <option value="">Keep in {selectedClass.display_name}</option>
                    {classes
                      .filter(c => c.id !== selectedClass.id)
                      .map(c => (
                        <option key={c.id} value={c.id}>
                          Move to {c.display_name} ({c.academic_year})
                        </option>
                      ))}
                  </select>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setEditingStudent(null)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingEditStudent}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {savingEditStudent ? "Saving..." : "Save Changes"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Confirmation Modal for Broadcast */}
        {showConfirmBroadcastModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center gap-3 text-yellow-400 mb-3">
                <AlertCircle className="w-6 h-6" />
                <h3 className="text-base font-bold text-white">Confirm Class Broadcast</h3>
              </div>
              <p className="text-xs text-gray-300 leading-relaxed">
                You are about to dispatch this announcement to{" "}
                <span className="font-bold text-white">{broadcastRecipientCount} student(s)</span> in{" "}
                <span className="font-bold text-blue-400">Class {selectedClass.display_name}</span>.
                {broadcastForm.send_email && " An email notification will also be dispatched."}
              </p>
              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowConfirmBroadcastModal(false)}
                  className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={broadcasting}
                  onClick={handleBroadcastSubmit}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                >
                  {broadcasting ? "Dispatching..." : "Confirm & Send"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Assignment Creation Modal */}
        {showAssignmentModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">New Assignment for {selectedClass.display_name}</h3>
                <button onClick={() => setShowAssignmentModal(false)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleCreateAssignment} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Title *</label>
                  <input
                    required
                    placeholder="e.g. Unit 3 Calculus Practice"
                    value={assignmentForm.title}
                    onChange={e => setAssignmentForm(f => ({ ...f, title: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Due Date *</label>
                    <input
                      required
                      type="date"
                      value={assignmentForm.due_date}
                      onChange={e => setAssignmentForm(f => ({ ...f, due_date: e.target.value }))}
                      className={inp}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Max Marks</label>
                    <input
                      type="number"
                      value={assignmentForm.max_marks}
                      onChange={e => setAssignmentForm(f => ({ ...f, max_marks: e.target.value }))}
                      className={inp}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Description</label>
                  <textarea
                    rows={3}
                    placeholder="Assignment description..."
                    value={assignmentForm.description}
                    onChange={e => setAssignmentForm(f => ({ ...f, description: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Optional Attachment File</label>
                  <input
                    type="file"
                    onChange={e => setAssignmentFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-purple-600 file:text-white"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAssignmentModal(false)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAssignment}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {submittingAssignment ? "Creating..." : "Create Assignment"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Note Upload Modal */}
        {showNoteModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Upload Note for {selectedClass.display_name}</h3>
                <button onClick={() => setShowNoteModal(false)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleUploadNote} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Title *</label>
                  <input
                    required
                    placeholder="e.g. Chapter 4 Lecture Notes"
                    value={noteForm.title}
                    onChange={e => setNoteForm(f => ({ ...f, title: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Subject</label>
                  <input
                    placeholder="e.g. Mathematics"
                    value={noteForm.subject}
                    onChange={e => setNoteForm(f => ({ ...f, subject: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Description</label>
                  <textarea
                    rows={2}
                    placeholder="Brief summary..."
                    value={noteForm.description}
                    onChange={e => setNoteForm(f => ({ ...f, description: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Document File *</label>
                  <input
                    required
                    type="file"
                    onChange={e => setNoteFile(e.target.files?.[0] || null)}
                    className="w-full text-xs text-gray-300 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white"
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowNoteModal(false)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingNote}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {submittingNote ? "Uploading..." : "Share Note"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Announcement Modal */}
        {showAnnouncementModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">Post Announcement — {selectedClass.display_name}</h3>
                <button onClick={() => setShowAnnouncementModal(false)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleCreateAnnouncement} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Title *</label>
                  <input
                    required
                    placeholder="Announcement title"
                    value={announcementForm.title}
                    onChange={e => setAnnouncementForm(f => ({ ...f, title: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Content *</label>
                  <textarea
                    required
                    rows={4}
                    placeholder="Announcement message..."
                    value={announcementForm.content}
                    onChange={e => setAnnouncementForm(f => ({ ...f, content: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAnnouncementModal(false)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingAnnouncement}
                    className="px-4 py-2 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                  >
                    {submittingAnnouncement ? "Posting..." : "Post Announcement"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Category Modal for Marks */}
        {showCatModal && (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white">New Assessment Category</h3>
                <button onClick={() => setShowCatModal(false)} className="text-gray-500 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleCreateCategory} className="space-y-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Category Name *</label>
                  <input
                    required
                    placeholder="e.g. Midterm 1, Final Exam, Quiz 2"
                    value={catForm.name}
                    onChange={e => setCatForm(f => ({ ...f, name: e.target.value }))}
                    className={inp}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Max Marks</label>
                    <input
                      required
                      type="number"
                      value={catForm.max_marks}
                      onChange={e => setCatForm(f => ({ ...f, max_marks: e.target.value }))}
                      className={inp}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-400 block mb-1">Weightage (%)</label>
                    <input
                      required
                      type="number"
                      value={catForm.weightage}
                      onChange={e => setCatForm(f => ({ ...f, weightage: e.target.value }))}
                      className={inp}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCatModal(false)}
                    className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-semibold rounded-xl"
                  >
                    Create Category
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // VIEW: Main Classes Grid / Hub
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-blue-400" /> School Classes Hub
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Manage grade sections, class rosters, and scoped academic communication.
          </p>
        </div>
        <button
          onClick={() => setShowCreateClassModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition-colors"
        >
          <Plus className="w-4 h-4" /> New Class
        </button>
      </div>

      {loading ? (
        <div className="p-12 text-center text-gray-500">Loading classes...</div>
      ) : classes.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-12 text-center">
          <BookOpen className="w-12 h-12 text-gray-700 mx-auto mb-4" />
          <p className="text-gray-400">No school classes found. Create your first class above.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {classes.map(cls => (
            <div
              key={cls.id}
              onClick={() => setSelectedClass(cls)}
              className="bg-gray-900 border border-gray-800 hover:border-blue-500/50 rounded-2xl p-5 cursor-pointer transition-all hover:shadow-lg hover:shadow-blue-500/5 group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors">
                    Class {cls.display_name}
                  </h3>
                  <p className="text-xs text-gray-400 mt-0.5">{cls.academic_year}</p>
                </div>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                  cls.is_active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                }`}>
                  {cls.is_active ? "Active" : "Archived"}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-5 pt-4 border-t border-gray-800 text-xs">
                <div>
                  <span className="text-gray-500 block">Enrolled Students</span>
                  <span className="text-base font-bold text-white">{cls.student_count}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Class Admins</span>
                  <span className="text-xs font-medium text-gray-300 truncate block">
                    {cls.admins?.length > 0
                      ? cls.admins.map(a => a.full_name || a.email.split("@")[0]).join(", ")
                      : "Global Admin"}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-800/60 flex items-center justify-between text-xs text-blue-400 group-hover:text-blue-300 font-medium">
                <span>Manage Workspace & Roster</span>
                <span className="group-hover:translate-x-1 transition-transform">→</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Class Modal */}
      {showCreateClassModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-white">Create New School Class</h3>
              <button onClick={() => setShowCreateClassModal(false)} className="text-gray-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateClass} className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Class / Grade Name *</label>
                <input
                  required
                  placeholder="e.g. 10 or 12 or B.Tech"
                  value={createClassForm.name}
                  onChange={e => setCreateClassForm(f => ({ ...f, name: e.target.value }))}
                  className={inp}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Section *</label>
                  <input
                    required
                    placeholder="e.g. A"
                    value={createClassForm.section}
                    onChange={e => setCreateClassForm(f => ({ ...f, section: e.target.value.toUpperCase() }))}
                    className={inp}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-400 block mb-1">Academic Year *</label>
                  <input
                    required
                    placeholder="2024-2025"
                    value={createClassForm.academic_year}
                    onChange={e => setCreateClassForm(f => ({ ...f, academic_year: e.target.value }))}
                    className={inp}
                  />
                </div>
              </div>
              <p className="text-[11px] text-gray-500">
                Display name will be generated as: <code className="text-blue-400">{createClassForm.name || "10"}-{createClassForm.section || "A"}</code>
              </p>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateClassModal(false)}
                  className="px-4 py-2 text-xs text-gray-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingClass}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl"
                >
                  {submittingClass ? "Creating..." : "Create Class"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
