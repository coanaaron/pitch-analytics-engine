import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper specifically for the Past Games tab card headers
const formatGameCardHeader = (game) => {
  const home = game.home_team || game.HomeTeam || '';
  const away = game.away_team || game.AwayTeam || '';

  const isMin = (teamStr) => /MIN|GOL|GOPHER|MINNESOTA/i.test(String(teamStr));

  // Determine Minnesota's opponent
  if (home || away) {
    if (isMin(home) && away && !isMin(away)) {
      return `vs ${away}`;
    }
    if (isMin(away) && home && !isMin(home)) {
      return `@ ${home}`;
    }
    if (home && !isMin(home)) return `vs ${home}`;
    if (away && !isMin(away)) return `@ ${away}`;
  }

  return game.opponent || `Game ID: ${game.game_i_d}`;
};

export default function App() {
  const [activePage, setActivePage] = useState('home');
  const [reportData, setReportData] = useState(null);
  const [selectedPitcher, setSelectedPitcher] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Past games storage & search states
  const [pastGames, setPastGames] = useState([]);
  const [searchDate, setSearchDate] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  // Fetch unique past games from metadata endpoint
  const fetchPastGames = useCallback(async () => {
    setIsLoadingHistory(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/metadata`);
      if (response.ok) {
        const data = await response.json();
        
        // Group metadata records by unique game_i_d
        const gamesMap = {};
        data.forEach((item) => {
          if (!gamesMap[item.game_i_d]) {
            gamesMap[item.game_i_d] = {
              game_i_d: item.game_i_d,
              date: item.date,
              opponent: item.opponent,
              home_team: item.home_team,
              away_team: item.away_team,
              stadium: item.stadium,
              pitchers: [item.pitcher],
            };
          } else {
            if (!gamesMap[item.game_i_d].pitchers.includes(item.pitcher)) {
              gamesMap[item.game_i_d].pitchers.push(item.pitcher);
            }
          }
        });

        // Convert to array and sort by Date (descending - newest first)
        const sortedGames = Object.values(gamesMap).sort((a, b) => {
          const dateA = new Date(a.date || '1970-01-01');
          const dateB = new Date(b.date || '1970-01-01');
          return dateB - dateA;
        });

        setPastGames(sortedGames);
      }
    } catch (err) {
      console.error('Failed to load game history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Refresh history whenever switching to Past Games tab
  useEffect(() => {
    if (activePage === 'past-games') {
      fetchPastGames();
    }
  }, [activePage, fetchPastGames]);

  // Filtered games based on user date or opponent search query
  const filteredPastGames = useMemo(() => {
    if (!searchDate.trim()) return pastGames;
    const query = searchDate.toLowerCase();
    return pastGames.filter(
      (game) =>
        (game.date && game.date.toLowerCase().includes(query)) ||
        (game.opponent && game.opponent.toLowerCase().includes(query)) ||
        (game.home_team && game.home_team.toLowerCase().includes(query)) ||
        (game.away_team && game.away_team.toLowerCase().includes(query)) ||
        (game.game_i_d && String(game.game_i_d).toLowerCase().includes(query))
    );
  }, [pastGames, searchDate]);

  // Handle CSV file upload
  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status: ${response.status}`);
      }

      const data = await response.json();
      setReportData(data);

      const metricsList = Array.isArray(data?.pitch_metrics) ? data.pitch_metrics : [];
      const boxList = Array.isArray(data?.box_score) ? data.box_score : [];
      const metaList = Array.isArray(data?.metadata) ? data.metadata : [];

      const pitchers = Array.from(
        new Set([
          ...metricsList.map((p) => p.pitcher),
          ...boxList.map((b) => b.pitcher),
          ...metaList.map((m) => m.pitcher),
        ].filter(Boolean))
      );

      if (pitchers.length > 0) {
        setSelectedPitcher(pitchers[0]);
      }
    } catch (err) {
      console.error(err);
      setError('Failed to process CSV file. Ensure backend server is running on port 8000.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch and load a historical game by game_i_d
  const loadHistoricalGame = async (gameId) => {
    setIsLoading(true);
    setError(null);
    try {
      const [metaRes, boxRes, metricsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/metadata?game_i_d=${gameId}`),
        fetch(`${API_BASE_URL}/api/v1/box-score?game_i_d=${gameId}`),
        fetch(`${API_BASE_URL}/api/v1/pitch-metrics?game_i_d=${gameId}`),
      ]);

      const metadata = await metaRes.json();
      const box_score = await boxRes.json();
      const pitch_metrics = await metricsRes.json();

      const combinedData = { metadata, box_score, pitch_metrics };
      setReportData(combinedData);

      const pitchers = Array.from(
        new Set([
          ...pitch_metrics.map((p) => p.pitcher),
          ...box_score.map((b) => b.pitcher),
          ...metadata.map((m) => m.pitcher),
        ].filter(Boolean))
      );

      if (pitchers.length > 0) {
        setSelectedPitcher(pitchers[0]);
      }

      setActivePage('home');
    } catch (err) {
      console.error('Failed to load past game:', err);
      setError('Could not load selected game data from database.');
    } finally {
      setIsLoading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    multiple: false,
  });

  const pitcherList = useMemo(() => {
    if (!reportData) return [];
    const metricsList = Array.isArray(reportData?.pitch_metrics) ? reportData.pitch_metrics : [];
    const boxList = Array.isArray(reportData?.box_score) ? reportData.box_score : [];
    const metaList = Array.isArray(reportData?.metadata) ? reportData.metadata : [];

    return Array.from(
      new Set([
        ...metricsList.map((p) => p.pitcher),
        ...boxList.map((b) => b.pitcher),
        ...metaList.map((m) => m.pitcher),
      ].filter(Boolean))
    );
  }, [reportData]);

  const meta = useMemo(() => {
    if (!reportData?.metadata) return {};
    if (Array.isArray(reportData.metadata)) {
      return reportData.metadata.find((m) => m.pitcher === selectedPitcher) || reportData.metadata[0] || {};
    }
    return reportData.metadata;
  }, [reportData, selectedPitcher]);

  const boxScore = useMemo(() => {
    if (!reportData?.box_score) return {};
    if (Array.isArray(reportData.box_score)) {
      return reportData.box_score.find((b) => b.pitcher === selectedPitcher) || reportData.box_score[0] || {};
    }
    return reportData.box_score;
  }, [reportData, selectedPitcher]);

  const filteredMetrics = useMemo(() => {
    if (!Array.isArray(reportData?.pitch_metrics)) return [];
    return reportData.pitch_metrics.filter((p) => p.pitcher === selectedPitcher);
  }, [reportData, selectedPitcher]);

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-6 print:p-0 print:bg-white print:text-black">
      
      {/* Top Navigation */}
      <nav className="flex gap-4 mb-8 border-b border-zinc-800 pb-4 max-w-7xl mx-auto print:hidden">
        <button 
          onClick={() => setActivePage('home')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activePage === 'home' ? 'bg-[#7a0016] text-white' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
        >
          Upload & Report Card
        </button>

        <button 
          onClick={() => setActivePage('past-games')}
          className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
            activePage === 'past-games' ? 'bg-[#7a0016] text-white' : 'text-zinc-400 hover:bg-zinc-900'
          }`}
        >
          Past Games
        </button>
      </nav>

      {/* PAGE 1: UPLOAD & REPORT */}
      {activePage === 'home' && (
        <main className="max-w-[1400px] mx-auto grid grid-cols-1 xl:grid-cols-12 gap-6 items-start print:block">
          
          {/* Upload Dropzone */}
          <section className="xl:col-span-3 space-y-4 print:hidden">
            <div>
              <h1 className="text-xl font-bold">Import Game Data</h1>
              <p className="text-zinc-400 text-xs mt-1">
                Upload raw TrackMan `.csv` export file to view full metrics report card.
              </p>
            </div>

            <div 
              {...getRootProps()} 
              className={`border-2 border-dashed transition-colors rounded-xl p-6 text-center cursor-pointer flex flex-col items-center justify-center min-h-[280px] ${
                isDragActive 
                  ? 'border-[#7a0016] bg-[#7a0016]/10' 
                  : 'border-zinc-700 hover:border-[#7a0016] bg-zinc-900/40'
              }`}
            >
              <input {...getInputProps()} />
              
              <div className="p-3 bg-zinc-800 rounded-full mb-3 text-[#7a0016]">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>

              {isLoading ? (
                <p className="text-zinc-300 text-xs font-medium animate-pulse">Processing data...</p>
              ) : isDragActive ? (
                <p className="text-[#a81c37] text-xs font-semibold">Drop file here...</p>
              ) : (
                <>
                  <p className="text-zinc-200 text-xs font-semibold">Drag & drop TrackMan CSV</p>
                  <button className="mt-3 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold rounded-md border border-zinc-700 transition-colors">
                    Browse
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

          {/* Printable Report Card */}
          <section className="xl:col-span-9 space-y-3 print:w-full">
            
            {/* Action Bar */}
            <div className="flex items-center justify-between print:hidden">
              <span className="text-xs text-zinc-400 font-medium">Report Card Live Preview</span>
              
              {reportData && (
                <div className="flex items-center gap-3">
                  {pitcherList.length > 0 && (
                    <div className="flex items-center gap-2">
                      <label className="text-xs font-semibold text-zinc-400">Pitcher:</label>
                      <select
                        value={selectedPitcher}
                        onChange={(e) => setSelectedPitcher(e.target.value)}
                        className="bg-zinc-800 text-zinc-100 text-xs font-semibold py-1.5 px-3 rounded-md border border-zinc-700 focus:outline-none focus:border-[#7a0016] cursor-pointer"
                      >
                        {pitcherList.map((pitcher, idx) => (
                          <option key={idx} value={pitcher}>
                            {pitcher}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}

                  <button 
                    onClick={() => window.print()}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-md border border-zinc-700 transition-colors flex items-center gap-1.5"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                    </svg>
                    Print / Save PDF
                  </button>
                </div>
              )}
            </div>

            {!reportData ? (
              <div className="bg-zinc-900/40 border-2 border-dashed border-zinc-800 rounded-xl p-12 min-h-[360px] flex flex-col items-center justify-center text-center">
                <p className="text-zinc-400 font-medium">No Pitch Data Loaded</p>
                <p className="text-xs text-zinc-500 max-w-sm mt-1">
                  Upload a TrackMan CSV on the left or select a previously saved game from the <span className="text-[#a81c37] hover:underline cursor-pointer font-semibold" onClick={() => setActivePage('past-games')}>Past Games</span> tab.
                </p>
              </div>
            ) : (
              <div className="bg-white text-zinc-900 rounded-xl p-4 shadow-xl border border-zinc-200 print:shadow-none print:border-none print:p-0">
                
                {/* MAROON HEADER BOX */}
                <div className="bg-[#7a0016] text-white rounded-lg p-3.5 font-sans shadow-inner space-y-2.5 print:[print-color-adjust:exact] print:bg-[#7a0016] print:text-white">
                  
                  {/* Pitcher Header Info */}
                  <div className="flex items-start justify-between">
                    <div>
                      <h1 className="text-2xl font-black tracking-tight leading-none print:text-white">
                        {selectedPitcher || meta.pitcher || 'Pitcher Name'}
                        {meta.handedness ? ` ${meta.handedness}` : ''}
                      </h1>
                      <p className="text-xs text-zinc-200 font-medium mt-1 print:text-zinc-100">
                        {meta.date || 'Date N/A'} · {meta.opponent || meta.game_i_d} {meta.stadium ? `· ${meta.stadium}` : ''}
                      </p>
                    </div>

                    {/* Start Grade Badge */}
                    {boxScore.start_grade && (
                      <div className="bg-[#5a0010] border border-white/30 rounded-lg px-2.5 py-0.5 text-center print:bg-[#5a0010] print:border-white/40">
                        <span className="text-[9px] uppercase block text-zinc-200 font-bold print:text-zinc-100">Grade</span>
                        <span className="text-base font-black leading-none print:text-white">{boxScore.start_grade}</span>
                      </div>
                    )}
                  </div>

                  {/* BOX SCORE ROW */}
                  <div className="bg-[#5a0010] border border-white/25 rounded-md p-2 flex items-center justify-between text-xs font-semibold print:bg-[#5a0010] print:border-white/30 print:[print-color-adjust:exact]">
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">IP</span><span className="text-white font-bold">{boxScore.ip ?? '-'}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">H</span><span className="text-white font-bold">{boxScore.h ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">R</span><span className="text-white font-bold">{boxScore.r ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">2B</span><span className="text-white font-bold">{boxScore.two_b ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">3B</span><span className="text-white font-bold">{boxScore.three_b ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">HR</span><span className="text-white font-bold">{boxScore.hr ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">BB</span><span className="text-white font-bold">{boxScore.bb ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">K</span><span className="text-white font-bold">{boxScore.k ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">HBP</span><span className="text-white font-bold">{boxScore.hbp ?? 0}</span></div>
                    <div className="text-center"><span className="text-zinc-300 text-[9px] uppercase block font-medium print:text-zinc-200">Pitches</span><span className="text-white font-bold">{boxScore.pitches ?? '-'}</span></div>
                  </div>

                </div>

                {/* COMPACT ALL-METRICS TABLE */}
                <div className="mt-3 border border-zinc-200 rounded-md p-2 bg-zinc-50/50 print:bg-white print:border-zinc-300">
                  <h2 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5 print:text-zinc-700">
                    PITCH METRICS
                  </h2>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-[10px] text-center border-collapse">
                      <thead>
                        <tr className="border-b border-zinc-300 text-zinc-600 bg-zinc-100/80 font-bold uppercase tracking-tight print:bg-zinc-100 print:text-zinc-900 print:[print-color-adjust:exact]">
                          <th className="p-1 text-left">Pitch</th>
                          <th className="p-1">#</th>
                          <th className="p-1">Velo</th>
                          <th className="p-1">Max</th>
                          <th className="p-1">Spin</th>
                          <th className="p-1">IVB</th>
                          <th className="p-1">HB</th>
                          <th className="p-1">VAA</th>
                          <th className="p-1">HRel</th>
                          <th className="p-1">VRel</th>
                          <th className="p-1">Ext</th>
                          <th className="p-1">Axis</th>
                          <th className="p-1">Strk</th>
                          <th className="p-1">Whf</th>
                          <th className="p-1">Whf%</th>
                          <th className="p-1">CSW%</th>
                          <th className="p-1">HH</th>
                          <th className="p-1">InPlay</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-200 text-zinc-800 font-mono text-[10px] print:divide-zinc-300 print:text-black">
                        {filteredMetrics.length === 0 ? (
                          <tr>
                            <td colSpan="18" className="p-3 text-center text-zinc-400 font-sans">
                              No metrics found for {selectedPitcher}
                            </td>
                          </tr>
                        ) : (
                          filteredMetrics.map((row, idx) => (
                            <tr key={idx} className="hover:bg-zinc-100/60 transition-colors">
                              <td className="p-1 text-left font-sans font-bold">
                                {row.tagged_pitch_type}
                              </td>
                              <td className="p-1 font-bold">{row.pitch_count ?? '-'}</td>
                              <td className="p-1">{row.avg_velo ? row.avg_velo.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.max_velo ? row.max_velo.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.avg_spin ? Math.round(row.avg_spin) : '-'}</td>
                              <td className="p-1">{row.avg_ver_break ? row.avg_ver_break.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.avg_hor_break ? row.avg_hor_break.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.avg_vaa ? row.avg_vaa.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.horz_rel ? row.horz_rel.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.vert_rel ? row.vert_rel.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.ext ? row.ext.toFixed(1) : '-'}</td>
                              <td className="p-1">{row.spin_axis ? Math.round(row.spin_axis) : '-'}</td>
                              <td className="p-1">{row.strike_count ?? '-'}</td>
                              <td className="p-1">{row.whiff_count ?? '-'}</td>
                              <td className="p-1 font-semibold">{row.whiff_pct !== null && row.whiff_pct !== undefined ? `${row.whiff_pct.toFixed(0)}%` : '-'}</td>
                              <td className="p-1 font-semibold">{row.csw_pct !== null && row.csw_pct !== undefined ? `${row.csw_pct.toFixed(0)}%` : '-'}</td>
                              <td className="p-1">{row.hard_hit ?? 0}</td>
                              <td className="p-1">{row.in_play ?? 0}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}
          </section>

        </main>
      )}

      {/* PAGE 2: PAST GAMES HISTORY */}
      {activePage === 'past-games' && (
        <section className="max-w-5xl mx-auto space-y-6 print:hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold">Past Uploaded Games</h1>
              <p className="text-zinc-400 text-sm mt-1">
                Select any previously processed TrackMan game file from the database to populate the report card sheet.
              </p>
            </div>

            {/* Date / Opponent Search Input */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search date (e.g. 2026-05) or opponent..."
                  value={searchDate}
                  onChange={(e) => setSearchDate(e.target.value)}
                  className="bg-zinc-900 text-zinc-100 text-xs px-3.5 py-2 pl-9 rounded-lg border border-zinc-700 focus:outline-none focus:border-[#7a0016] w-64 md:w-80"
                />
                <svg
                  className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
              </div>

              <button
                onClick={fetchPastGames}
                className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-xs font-semibold rounded-lg border border-zinc-700 transition-colors shrink-0"
              >
                Refresh List
              </button>
            </div>
          </div>

          {isLoadingHistory ? (
            <div className="p-12 text-center text-zinc-400 bg-zinc-900/40 rounded-xl border border-zinc-800 animate-pulse">
              Loading saved games from PostgreSQL...
            </div>
          ) : filteredPastGames.length === 0 ? (
            <div className="p-12 text-center text-zinc-500 bg-zinc-900/40 rounded-xl border border-zinc-800">
              {searchDate
                ? `No games found matching date or opponent "${searchDate}".`
                : 'No previous games found in database. Upload a CSV on the main page to populate history.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredPastGames.map((game) => (
                <div
                  key={game.game_i_d}
                  onClick={() => loadHistoricalGame(game.game_i_d)}
                  className="bg-zinc-900/60 border border-zinc-800 hover:border-[#7a0016] rounded-xl p-4 cursor-pointer transition-all hover:scale-[1.01] hover:shadow-lg space-y-3 group"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] uppercase tracking-wider text-[#a81c37] font-bold">
                        📅 {game.date || 'Date N/A'}
                      </span>
                      <h3 className="text-base font-bold text-zinc-100 group-hover:text-[#a81c37] transition-colors">
                        {formatGameCardHeader(game)}
                      </h3>
                    </div>
                    <span className="text-[10px] bg-zinc-800 text-zinc-400 font-mono px-2 py-0.5 rounded border border-zinc-700">
                      {game.game_i_d}
                    </span>
                  </div>

                  {game.stadium && (
                    <p className="text-xs text-zinc-400">
                      📍 {game.stadium}
                    </p>
                  )}

                  <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between text-xs text-zinc-400">
                    <span>
                      {game.pitchers?.length || 0} Pitcher{game.pitchers?.length === 1 ? '' : 's'} recorded
                    </span>
                    <span className="text-[#a81c37] font-medium text-[11px] group-hover:translate-x-1 transition-transform">
                      Load Report →
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

    </div>
  );
}