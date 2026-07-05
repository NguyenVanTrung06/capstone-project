import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, 
  Send, 
  Calendar as CalendarIcon, 
  CheckSquare, 
  BookOpen, 
  Clock, 
  AlertCircle, 
  Check, 
  Plus, 
  ChevronLeft, 
  Terminal, 
  Activity,
  User,
  ShieldCheck,
  Trash2
} from 'lucide-react';

export default function App() {
  const [messages, setMessages] = useState([
    { 
      sender: 'assistant', 
      text: "Hello! I am OmniPilot AI, your multi-agent personal scheduler and exam helper. How can I help you organize your studies and tasks today?" 
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [telemetry, setTelemetry] = useState([]);
  const [activeTab, setActiveTab] = useState('tasks');
  const [tasks, setTasks] = useState([]);
  const [calendar, setCalendar] = useState([]);
  const [studyGuides, setStudyGuides] = useState([]);
  const [viewingGuide, setViewingGuide] = useState(null);
  const [currentAgent, setCurrentAgent] = useState('Planner Agent');

  // Input states for manual additions
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('Medium');
  const [newTaskDueDate, setNewTaskDueDate] = useState('');

  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventStart, setNewEventStart] = useState('');
  const [newEventEnd, setNewEventEnd] = useState('');
  const [newEventDesc, setNewEventDesc] = useState('');

  const chatEndRef = useRef(null);

  // Fetch initial data & initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        await fetch('/api/session/init', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: 'omnipilot-dashboard' })
        });
      } catch (err) {
        console.error("Error initializing session:", err);
      } finally {
        fetchTasks();
        fetchCalendar();
        fetchStudyGuides();
      }
    };
    initSession();
  }, []);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/tasks');
      if (res.ok) {
        const data = await res.json();
        setTasks(data);
      }
    } catch (err) {
      console.error("Error fetching tasks:", err);
    }
  };

  const fetchCalendar = async () => {
    try {
      const res = await fetch('/api/calendar');
      if (res.ok) {
        const data = await res.json();
        setCalendar(data);
      }
    } catch (err) {
      console.error("Error fetching calendar:", err);
    }
  };

  const fetchStudyGuides = async () => {
    try {
      const res = await fetch('/api/study-guides');
      if (res.ok) {
        const data = await res.json();
        setStudyGuides(data);
      }
    } catch (err) {
      console.error("Error fetching study guides:", err);
    }
  };

  const fetchGuideContent = async (filename) => {
    try {
      const res = await fetch(`/api/study-guides/${filename}`);
      if (res.ok) {
        const data = await res.json();
        setViewingGuide(data);
      }
    } catch (err) {
      console.error("Error fetching study guide details:", err);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMsg = inputValue;
    setMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setInputValue('');
    setLoading(true);
    setTelemetry([]);

    // Telemetry simulation during loading
    const agents = ['Planner Agent', 'Task Optimization Agent', 'Exam/Study Agent', 'Life Scheduler Agent'];
    let agentIdx = 0;
    const interval = setInterval(() => {
      setCurrentAgent(agents[agentIdx % agents.length]);
      agentIdx++;
    }, 1500);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, session_id: 'omnipilot-dashboard' })
      });

      clearInterval(interval);
      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, { sender: 'assistant', text: data.response }]);
        setTelemetry(data.telemetry);
        setCurrentAgent('Planner Agent');
        
        // Refresh dashboard states as agents might have modified things
        fetchTasks();
        fetchCalendar();
        fetchStudyGuides();
      } else {
        const errData = await response.json();
        setMessages(prev => [...prev, { 
          sender: 'assistant', 
          text: `Sorry, I encountered an error: ${errData.detail || 'Could not communicate with the backend agents.'}` 
        }]);
      }
    } catch (err) {
      clearInterval(interval);
      setMessages(prev => [...prev, { 
        sender: 'assistant', 
        text: "Error: Could not connect to OmniPilot backend. Make sure the FastAPI server is running." 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTaskTitle.trim() || !newTaskDueDate) return;

    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle,
          priority: newTaskPriority,
          due_date: newTaskDueDate,
          status: 'Todo'
        })
      });
      if (res.ok) {
        setNewTaskTitle('');
        setNewTaskDueDate('');
        fetchTasks();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleTaskStatus = async (task) => {
    const nextStatus = task.status === 'Done' ? 'Todo' : 'Done';
    try {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...task,
          status: nextStatus
        })
      });
      if (res.ok) {
        fetchTasks();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchTasks();
      }
    } catch (err) {
      console.error("Error deleting task:", err);
    }
  };

  const handleCreateEvent = async (e) => {
    e.preventDefault();
    if (!newEventTitle.trim() || !newEventStart || !newEventEnd) return;

    try {
      const res = await fetch('/api/calendar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newEventTitle,
          start_time: newEventStart,
          end_time: newEventEnd,
          description: newEventDesc
        })
      });
      if (res.ok) {
        setNewEventTitle('');
        setNewEventStart('');
        setNewEventEnd('');
        setNewEventDesc('');
        fetchCalendar();
      } else {
        const data = await res.json();
        alert(data.detail || "Error scheduling event");
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header glass-panel">
        <div className="logo-container">
          <div className="logo-icon">OP</div>
          <div>
            <h1 className="logo-text">OmniPilot AI</h1>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Multi-Agent Orchestrator</span>
          </div>
        </div>
        <div className="connection-status">
          <ShieldCheck size={16} className="status-dot" style={{ color: 'var(--accent-green)' }} />
          <span>Local Engine Secure</span>
        </div>
      </header>

      {/* Main Grid */}
      <main className="dashboard-grid">
        {/* Left Side: Chat & Telemetry */}
        <section className="left-panel">
          {/* Chat Window */}
          <div className="chat-section glass-panel">
            <div className="chat-messages">
              {messages.map((m, idx) => (
                <div key={idx} className={`message ${m.sender}`}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {m.sender === 'user' ? <User size={12} /> : <Activity size={12} />}
                    <span style={{ fontWeight: 600 }}>{m.sender === 'user' ? 'You' : 'OmniPilot AI'}</span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                </div>
              ))}
              {loading && (
                <div className="message assistant" style={{ opacity: 0.7 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Activity size={16} className="status-dot" />
                    <span>{currentAgent} is analyzing context...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSend} className="chat-input-area">
              <input
                type="text"
                className="chat-input"
                placeholder="Ask OmniPilot to schedule study, optimize tasks, create study guides..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={loading}
              />
              <button type="submit" className="chat-send-btn" disabled={loading}>
                <Send size={18} />
              </button>
            </form>
          </div>

          {/* Sub-agents visualizer & live telemetry logs */}
          <div className="telemetry-section glass-panel">
            <h3 className="telemetry-title">
              <Terminal size={16} />
              Agent Telemetry Logs
            </h3>
            
            {/* Visual Multi-Agent Node status */}
            <div className="agent-visualizer" style={{ marginBottom: '1rem' }}>
              <div className={`agent-node ${currentAgent === 'Planner Agent' || loading ? 'active' : ''}`}>
                <div className="agent-avatar">👑</div>
                <div className="agent-label">Planner</div>
              </div>
              <div className={`agent-node ${currentAgent === 'Task Optimization Agent' && loading ? 'active' : ''}`}>
                <div className="agent-avatar">📊</div>
                <div className="agent-label">Optimizer</div>
              </div>
              <div className={`agent-node ${currentAgent === 'Exam/Study Agent' && loading ? 'active' : ''}`}>
                <div className="agent-avatar">📖</div>
                <div className="agent-label">Study</div>
              </div>
              <div className={`agent-node ${currentAgent === 'Life Scheduler Agent' && loading ? 'active' : ''}`}>
                <div className="agent-avatar">📅</div>
                <div className="agent-label">Scheduler</div>
              </div>
            </div>

            <div className="telemetry-events">
              {telemetry.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', marginTop: '1rem' }}>
                  No active logs. Ask a query to view agent orchestrations.
                </div>
              ) : (
                telemetry.map((t, idx) => (
                  <div key={idx} className="telemetry-row">
                    <span className="telemetry-agent">[{t.agent_name}]</span>
                    <span className="telemetry-action">{t.action}:</span>
                    <span className="telemetry-details">{t.details}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Right Side: Tabbed panel (Tasks, Calendar, Study Guides) */}
        <section className="right-panel glass-panel">
          <div className="tab-headers">
            <button 
              className={`tab-btn ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => { setActiveTab('tasks'); setViewingGuide(null); }}
            >
              <CheckSquare size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Tasks Log
            </button>
            <button 
              className={`tab-btn ${activeTab === 'calendar' ? 'active' : ''}`}
              onClick={() => { setActiveTab('calendar'); setViewingGuide(null); }}
            >
              <CalendarIcon size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Calendar
            </button>
            <button 
              className={`tab-btn ${activeTab === 'study' ? 'active' : ''}`}
              onClick={() => { setActiveTab('study'); }}
            >
              <BookOpen size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
              Study Guides
            </button>
          </div>

          <div className="tab-content">
            {/* TASKS TAB */}
            {activeTab === 'tasks' && (
              <div className="tasks-tab">
                {/* Manual Add Form */}
                <form onSubmit={handleCreateTask} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                  <input
                    type="text"
                    className="chat-input"
                    style={{ flex: 2, padding: '0.5rem 1rem' }}
                    placeholder="New task title..."
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                  />
                  <select
                    className="chat-input"
                    style={{ flex: 0.8, padding: '0.5rem 1rem' }}
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(e.target.value)}
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                  <input
                    type="date"
                    className="chat-input"
                    style={{ flex: 1, padding: '0.5rem 1rem' }}
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                  />
                  <button type="submit" className="chat-send-btn" style={{ width: 'auto', padding: '0 1rem', height: 'auto' }}>
                    <Plus size={18} />
                  </button>
                </form>

                {/* List */}
                <div className="tasks-list">
                  {tasks.length === 0 ? (
                    <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                      No tasks scheduled. Ask OmniPilot to organize your syllabus!
                    </div>
                  ) : (
                    tasks.map((task) => (
                      <div key={task.id} className="task-item">
                        <div className="task-info">
                          <button 
                            onClick={() => handleToggleTaskStatus(task)}
                            style={{ 
                              background: task.status === 'Done' ? 'var(--accent-green)' : 'transparent',
                              border: '2px solid var(--glass-border)',
                              borderRadius: '4px',
                              width: '20px',
                              height: '20px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center'
                            }}
                          >
                            {task.status === 'Done' && <Check size={12} style={{ color: '#000', strokeWidth: 3 }} />}
                          </button>
                          <span className="task-title" style={{ textDecoration: task.status === 'Done' ? 'line-through' : 'none', opacity: task.status === 'Done' ? 0.5 : 1 }}>
                            {task.title}
                          </span>
                        </div>
                        <div className="task-meta">
                          <span className={`priority-badge priority-${task.priority}`}>{task.priority}</span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                            <Clock size={12} />
                            {task.due_date}
                          </span>
                          <button
                            onClick={() => handleDeleteTask(task.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--accent-red)',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              padding: '0.25rem',
                              opacity: 0.6,
                              transition: 'var(--transition-smooth)'
                            }}
                            className="task-delete-btn"
                            title="Delete Task"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* CALENDAR TAB */}
            {activeTab === 'calendar' && (
              <div className="calendar-tab">
                {/* Manual Event Form */}
                <form onSubmit={handleCreateEvent} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      className="chat-input"
                      style={{ flex: 2, padding: '0.5rem 1rem' }}
                      placeholder="Event Title"
                      value={newEventTitle}
                      onChange={(e) => setNewEventTitle(e.target.value)}
                    />
                    <input
                      type="datetime-local"
                      className="chat-input"
                      style={{ flex: 1, padding: '0.5rem 1rem' }}
                      value={newEventStart}
                      onChange={(e) => setNewEventStart(e.target.value)}
                    />
                    <input
                      type="datetime-local"
                      className="chat-input"
                      style={{ flex: 1, padding: '0.5rem 1rem' }}
                      value={newEventEnd}
                      onChange={(e) => setNewEventEnd(e.target.value)}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input
                      type="text"
                      className="chat-input"
                      style={{ flex: 1, padding: '0.5rem 1rem' }}
                      placeholder="Brief Description"
                      value={newEventDesc}
                      onChange={(e) => setNewEventDesc(e.target.value)}
                    />
                    <button type="submit" className="chat-send-btn" style={{ width: 'auto', padding: '0 1.5rem', height: 'auto' }}>
                      Add Event
                    </button>
                  </div>
                </form>

                {/* Event Cards */}
                <div className="calendar-events">
                  {calendar.length === 0 ? (
                    <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                      No scheduled events. Ask OmniPilot to coordinate your timeslots!
                    </div>
                  ) : (
                    calendar.map((event) => (
                      <div key={event.id} className="calendar-event">
                        <div className="event-header">
                          <span className="event-title">{event.title}</span>
                          <span className="event-time">
                            {new Date(event.start_time).toLocaleString()} - {new Date(event.end_time).toLocaleTimeString()}
                          </span>
                        </div>
                        {event.description && <p className="event-desc">{event.description}</p>}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* STUDY GUIDES TAB */}
            {activeTab === 'study' && (
              <div className="study-tab">
                {!viewingGuide ? (
                  <div className="study-guides-grid">
                    {studyGuides.length === 0 ? (
                      <div style={{ gridColumn: 'span 2', color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                        No study guides generated yet. Ask OmniPilot to write one for you!
                      </div>
                    ) : (
                      studyGuides.map((filename, idx) => (
                        <div key={idx} className="guide-card" onClick={() => fetchGuideContent(filename)}>
                          <span className="guide-title">{filename.replace('.md', '').replace(/-/g, ' ')}</span>
                          <span className="guide-date">{filename}</span>
                        </div>
                      ))
                    )}
                  </div>
                ) : (
                  <div className="guide-viewer">
                    <button className="guide-back-btn" onClick={() => setViewingGuide(null)}>
                      <ChevronLeft size={14} style={{ marginRight: '0.25rem', verticalAlign: 'middle' }} />
                      Back to list
                    </button>
                    <div className="guide-content-box">
                      <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--glass-border)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
                        <h2 style={{ margin: 0, textTransform: 'capitalize' }}>
                          {viewingGuide.filename.replace('.md', '').replace(/-/g, ' ')}
                        </h2>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{viewingGuide.filename}</span>
                      </div>
                      {/* Simple custom markdown rendering */}
                      <div style={{ whiteSpace: 'pre-wrap' }}>
                        {viewingGuide.content}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
