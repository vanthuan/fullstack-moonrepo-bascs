import { useState } from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

interface DashboardState {
  user: User | null;
  isLoading: boolean;
  errorMessage: string | null;
}

export default function App() {
  const [searchEmail, setSearchEmail] = useState<string>('test@example.com');
  const [state, setState] = useState<DashboardState>({
    user: null,
    isLoading: false,
    errorMessage: null,
  });

  const handleFetchUser = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Toggle Loading state on, clear old errors
    setState((prev) => ({ ...prev, isLoading: true, errorMessage: null }));

    try {
      // Connect directly to our real running Python FastAPI proxy gateway
      const response = await fetch(`http://localhost:8000/api/user?email=${encodeURIComponent(searchEmail)}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`No user database entries match '${searchEmail}'`);
        }
        throw new Error('Server encountered an unhandled network exception.');
      }

      const data: User = await response.json();

      // Successfully load dynamic fields from Python database
      setState((prev) => ({
        ...prev,
        user: data,
        isLoading: false
      }));

    } catch (err: any) {
      // Deactivate spinner and assign visible error context
      setState((prev) => ({
        ...prev,
        user: null,
        isLoading: false,
        errorMessage: err.message || 'Fatal Connection Error'
      }));
    }
  };

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, sans-serif', maxWidth: '500px' }}>
      <h1>Moonrepo Monorepo Client</h1>
      
      <form onSubmit={handleFetchUser} style={{ marginBottom: '1.5rem' }}>
        <label htmlFor="email-search" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
          Search SQLite Database:
        </label>
        <input 
          id="email-search"
          type="email" 
          value={searchEmail} 
          onChange={(e) => setSearchEmail(e.target.value)}
          placeholder="Enter user email..."
          required
          style={{ padding: '0.5rem', marginRight: '0.5rem', width: '250px' }}
        />
        <button 
          type="submit" 
          disabled={state.isLoading}
          style={{ padding: '0.5rem 1rem', cursor: state.isLoading ? 'not-allowed' : 'pointer' }}
        >
          {state.isLoading ? 'Fetching...' : 'Query Database'}
        </button>
      </form>

      {state.errorMessage && (
        <div style={{ color: '#d32f2f', padding: '0.5rem', backgroundColor: '#ffebee', borderRadius: '4px' }}>
          ⚠️ {state.errorMessage}
        </div>
      )}

      {state.user && (
        <div style={{ marginTop: '1rem', border: '1px solid #4caf50', padding: '1rem', backgroundColor: '#e8f5e9', borderRadius: '4px' }}>
          <h3 style={{ marginTop: 0, color: '#2e7d32' }}>✅ Real FastAPI Data Retrieved</h3>
          <p><strong>Database ID:</strong> {state.user.id}</p>
          <p><strong>Full Name:</strong> {state.user.name}</p>
          <p><strong>Email Address:</strong> {state.user.email}</p>
        </div>
      )}
    </div>
  );
}
