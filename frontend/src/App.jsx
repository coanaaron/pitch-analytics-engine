import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

export default function App() {
  const [activePage, setActivePage] = useState('home');
  const [reportData, setReportData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // File Upload Handler connecting to FastAPI backend
  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Replace URL with your actual FastAPI endpoint URL if different
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status: ${response.status}`);
      }

      const data = await response.json();
      setReportData(data); // Stores the real parsed data from Python!
    } catch (err) {
      console.error(err);
      setError('Failed to process CSV file. Ensure backend server is running.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    multiple: false,
  });

  // Color helper for pitch types
  const getPitchColor = (pitchType) => {
    const type = pitchType?.toLowerCase() || '';
    if (type.includes('fastball') || type.includes('ff')) return 'bg-[#d9383a]';
    if (type.includes('change') || type.includes('ch')) return 'bg-[#20b2aa]';
    if (type.includes('curve') || type.includes('cb')) return 'bg-[#1e3d59]';
    if (type.includes('slider') || type.includes('sl')) return 'bg-[#4682b4]';
    return 'bg-zinc-400';
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 print:p-0 print:bg-white">
      
      {/* Top Navigation Bar - Hidden during printing */}
      <nav className="flex gap-4 mb-8 border-b border-zinc-800 pb-4 max-w-7xl mx-auto print:hidden">
        <button 
          onClick={() => setActivePage('home')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activePage === 'home' ? 'bg-red-700 text-white' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
        >
          Upload CSV
        </button>

        <button 
          onClick={() => setActivePage('calendar')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activePage === 'calendar' ? 'bg-red-700 text-white' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
        >
          Game Calendar
        </button>
      </nav>

      {/* PAGE 1: HOME / UPLOAD */}
      {activePage === 'home' && (
        <main className="max-w-7xl mx-auto grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
          
          {/* LEFT SIDE: Drag & Drop Zone (5 Cols) */}
          <section className="xl:col-span-4 space-y-4 print:hidden">
            <div>
              <h1 className="text-2xl font-bold">Import Game Data</h1>
              <p className="text-zinc-400 text-sm mt-1">
                Upload a raw TrackMan `.csv` export file to process metrics and view report card.
              </p>
            </div>

            {/* REACT DROPZONE CONTAINER */}
            <div 
              {...getRootProps()} 
              className={`border-2 border-dashed transition-colors rounded-xl p-8 text-center cursor-pointer flex flex-col items-center justify-center min-h-[320px] ${
                isDragActive 
                  ? 'border-red-500 bg-red-950/20' 
                  : 'border-zinc-700 hover:border-red-500 bg-zinc-900/40'
              }`}
            >
              <input {...getInputProps()} />
              
              <div className="p-3 bg-zinc-800 rounded-full mb-3 text-red-500">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>

              {isLoading ? (
                <p className="text-zinc-300 font-medium animate-pulse">Processing CSV with backend...</p>
              ) : isDragActive ? (
                <p className="text-red-400 font-semibold">Drop the TrackMan file here...</p>
              ) : (
                <>
                  <p className="text-zinc-200 font-semibold">Drag & drop your TrackMan CSV here</p>
                  <p className="text-xs text-zinc-500 mt-1">Supports standard CSV pitch tracking files</p>
                  <button className="mt-4 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold rounded-md border border-zinc-700 transition-colors">
                    Browse Files
                  </button>
                </>
              )}
            </div>

            {error && (
              <p className="text-xs text-red-400 bg-red-950/40 border border-red-800 p-3 rounded-md">
                {error}
              </p>
            )}
          </section>

          {/* RIGHT SIDE: Report Card View (8 Cols) */}
          <section className="xl:col-span-8 space-y-3">
            <div className="flex items-center justify-between print:hidden">
              <span className="text-xs text-zinc-400 font-medium">Report Card Live Preview</span>
              
              {reportData && (
                <button 
                  onClick={() => window.print()}
                  className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-md border border-zinc-700 transition-colors flex items-center gap-1.5"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                  </svg>
                  Print / Save PDF
                </button>
              )}
            </div>

            {/* IF NO DATA: Blank Canvas */}
            {!reportData ? (
              <div className="bg-zinc-900/40 border-2 border-dashed border-zinc-800 rounded-xl p-12 min-h-[360px] flex flex-col items-center justify-center text-center">
                <div className="p-3 bg-zinc-800/60 rounded-full mb-3 text-zinc-500">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <p className="text-zinc-400 font-medium">No Pitch Data Selected</p>
                <p className="text-xs text-zinc-500 max-w-sm mt-1">
                  Upload a TrackMan CSV on the left to automatically parse metrics and generate the printable post-game report card.
                </p>
              </div>
            ) : (
              /* IF REAL DATA RETURNED: Render Printable Sheet */
              <div className="bg-white text-zinc-900 rounded-xl p-4 shadow-xl border border-zinc-200 print:shadow-none print:border-none print:p-0">
                
                {/* CRIMSON HEADER BANNER */}
                <div className="bg-[#7a0016] text-white rounded-lg p-4 font-sans shadow-inner">
                  <div className="flex justify-between items-start">
                    
                    <div className="space-y-2">
                      <div>
                        <h1 className="text-2xl font-black tracking-tight leading-none">
                          {reportData.pitcher_name || 'Pitcher Name'} ({reportData.pitcher_hand || 'RHP'})
                        </h1>
                        <p className="text-xs text-zinc-300 font-medium mt-1">
                          {reportData.date || 'YYYY-MM-DD'} · vs {reportData.opponent || 'OPP'} · {reportData.venue || 'Venue'}
                        </p>
                      </div>

                      {/* Stat Badge Pill */}
                      <div className="inline-block bg-white/10 backdrop-blur-sm border border-white/20 rounded-md px-2.5 py-1 text-xs font-semibold tracking-wide">
                        {reportData.summary_line || '0 IP · 0 H · 0 R · 0 BB · 0 K · 0 Pitches'}
                      </div>

                      {/* Pitch Legend */}
                      <div className="flex items-center gap-3 text-xs pt-1">
                        {reportData.pitch_types?.map((p, idx) => (
                          <span key={idx} className="flex items-center gap-1 font-semibold">
                            <span className={`w-2.5 h-2.5 rounded-full ${getPitchColor(p.name)}`}></span> 
                            {p.name}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Start Grade */}
                    <div className="text-right">
                      <span className="text-[10px] font-bold tracking-wider uppercase text-zinc-300 block">START GRADE</span>
                      <span className="text-4xl font-black leading-none block my-0.5">{reportData.start_grade || 'N/A'}</span>
                      <span className="text-[10px] text-zinc-300 font-medium block">{reportData.grade_line || ''}</span>
                    </div>

                  </div>
                </div>

                {/* METRICS TABLE */}
                <div className="mt-4 border border-zinc-200 rounded-md p-3 bg-zinc-50/50">
                  <h2 className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider mb-2">PITCH TYPE METRICS</h2>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-[11px] text-center border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-300 text-zinc-600 bg-zinc-100/80 font-semibold">
                          <th className="p-1.5 text-left font-bold">Pitch</th>
                          <th className="p-1.5">Velo</th>
                          <th className="p-1.5">Velo Max</th>
                          <th className="p-1.5">#</th>
                          <th className="p-1.5">Strikes</th>
                          <th className="p-1.5">Whiffs</th>
                          <th className="p-1.5">Whiff%</th>
                          <th className="p-1.5">CSW%</th>
                          <th className="p-1.5">Spin</th>
                          <th className="p-1.5">VBreak</th>
                          <th className="p-1.5">HBreak</th>
                          <th className="p-1.5">VAA</th>
                          <th className="p-1.5">HorzRel</th>
                          <th className="p-1.5">VertRel</th>
                          <th className="p-1.5">Ext</th>
                          <th className="p-1.5">HardHit</th>
                          <th className="p-1.5">InPlay</th>
                          <th className="p-1.5">SpinAxis</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-200 text-zinc-800 font-medium">
                        {reportData.pitch_metrics?.map((row, idx) => (
                          <tr key={idx} className="hover:bg-zinc-100/50">
                            <td className="p-1.5 text-left font-bold flex items-center gap-1.5">
                              <span className={`w-2.5 h-2.5 rounded-full ${getPitchColor(row.pitch_name)} shrink-0`}></span> 
                              {row.pitch_name}
                            </td>
                            <td className="p-1.5">{row.velo}</td>
                            <td className="p-1.5">{row.velo_max}</td>
                            <td className="p-1.5">{row.count}</td>
                            <td className="p-1.5">{row.strikes}</td>
                            <td className="p-1.5">{row.whiffs}</td>
                            <td className="p-1.5">{row.whiff_pct}</td>
                            <td className="p-1.5">{row.csw_pct}</td>
                            <td className="p-1.5">{row.spin}</td>
                            <td className="p-1.5">{row.vbreak}</td>
                            <td className="p-1.5">{row.hbreak}</td>
                            <td className="p-1.5">{row.vaa}</td>
                            <td className="p-1.5">{row.horz_rel}</td>
                            <td className="p-1.5">{row.vert_rel}</td>
                            <td className="p-1.5">{row.extension}</td>
                            <td className="p-1.5">{row.hard_hit}</td>
                            <td className="p-1.5">{row.in_play}</td>
                            <td className="p-1.5">{row.spin_axis}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}
          </section>

        </main>
      )}

      {/* PAGE 2: CALENDAR HISTORY */}
      {activePage === 'calendar' && (
        <section className="max-w-4xl mx-auto space-y-4 print:hidden">
          <h1 className="text-2xl font-bold">Game & Session History</h1>
          <p className="text-zinc-400 text-sm">Select a date below to view recorded pitches and metrics.</p>

          <div className="p-6 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-400">
            [ Calendar View & Previous Games List Will Live Here ]
          </div>
        </section>
      )}

    </div>
  );
}
