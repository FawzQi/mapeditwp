<script>
  import WaypointEditor from './WaypointEditor.svelte';
  import TerminalEditor from './TerminalEditor.svelte';

  let mapData = [];
  let terminalData = [];
  let mapImageProps = null; 
  let activeTab = 'waypoint';
  
  // Track original filenames
  let waypointFileName = 'edited_waypoints.csv';
  let terminalFileName = 'edited_terminals.csv';
  
  // Toast Notification State
  let toastMessage = "";

  // --- LANGUAGE STATE & DICTIONARY ---
  let lang = 'en';

  const i18n = {
    en: {
      title: "Map Configurator",
      uploadMap: "Upload Map (.pgm & .yaml)",
      uploadWp: "Upload Waypoints (CSV)",
      uploadTerm: "Upload Terminals (CSV)",
      wpEditor: "📍 Waypoint Editor",
      termEditor: "🎯 Terminal Editor",
      emptyState: "📁 Please upload data or a Map image to begin editing.",
      errBothFiles: "⚠️ Please select BOTH the .pgm and .yaml/.yml files at the same time.",
      errPgmFormat: "Error: Only binary (P5) PGM files are supported.",
      errNoData: "⚠️ No data available to save.",
      successSave: "✅ Successfully saved"
    },
    id: {
      title: "Konfigurator Peta",
      uploadMap: "Unggah Peta (.pgm & .yaml)",
      uploadWp: "Unggah Waypoint (CSV)",
      uploadTerm: "Unggah Terminal (CSV)",
      wpEditor: "📍 Editor Waypoint",
      termEditor: "🎯 Editor Terminal",
      emptyState: "📁 Silakan unggah data atau gambar Peta untuk mulai mengedit.",
      errBothFiles: "⚠️ Harap pilih KEDUA file .pgm dan .yaml/.yml secara bersamaan.",
      errPgmFormat: "Galat: Hanya file PGM biner (P5) yang didukung.",
      errNoData: "⚠️ Tidak ada data yang tersedia untuk disimpan.",
      successSave: "✅ Berhasil menyimpan"
    }
  };

  function toggleLanguage() {
    lang = lang === 'en' ? 'id' : 'en';
  }
  // -----------------------------------

  function showToast(message) {
    toastMessage = message;
    setTimeout(() => {
      toastMessage = "";
    }, 3000);
  }

  function loadCsv(file, onComplete) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.trim().split('\n');
      if (lines.length < 2) return;

      const headerLine = lines[0].trim();
      let separator = ',';
      if (headerLine.includes('\t')) separator = '\t';
      else if (!headerLine.includes(',')) separator = /\s+/;

      const headers = headerLine.split(separator === /\s+/ ? /\s+/ : separator).map(h => h.trim());
      const parsedData = [];
      
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const values = line.split(separator === /\s+/ ? /\s+/ : separator);
        let row = {};
        headers.forEach((header, index) => {
           row[header] = parseFloat(values[index]);
        });
        parsedData.push(row);
      }
      onComplete(parsedData);
    };
    reader.readAsText(file);
  }

  function handleWaypointUpload(event) { 
    const file = event.target.files[0];
    if (file) {
      waypointFileName = file.name;
      loadCsv(file, data => mapData = data); 
    }
  }
  function handleTerminalUpload(event) { 
    const file = event.target.files[0];
    if (file) {
      terminalFileName = file.name;
      loadCsv(file, data => terminalData = data); 
    }
  }

  async function handleMapUpload(event) {
    const files = event.target.files;
    let pgmFile = null;
    let yamlFile = null;

    for (let file of files) {
      if (file.name.toLowerCase().endsWith('.pgm')) pgmFile = file;
      if (file.name.toLowerCase().endsWith('.yaml') || file.name.toLowerCase().endsWith('.yml')) yamlFile = file;
    }

    if (!pgmFile || !yamlFile) return alert(i18n[lang].errBothFiles);

    const yamlText = await yamlFile.text();
    const resMatch = yamlText.match(/resolution:\s*([\d.]+)/);
    const originMatch = yamlText.match(/origin:\s*\[\s*([\d.-]+)\s*,\s*([\d.-]+)(?:\s*,\s*([\d.-]+))?/);
    
    const resolution = resMatch ? parseFloat(resMatch[1]) : 0.05;
    const originX = originMatch ? parseFloat(originMatch[1]) : 0;
    const originY = originMatch ? parseFloat(originMatch[2]) : 0;
    const originYaw = (originMatch && originMatch[3]) ? parseFloat(originMatch[3]) : 0;

    const buffer = await pgmFile.arrayBuffer();
    const view = new Uint8Array(buffer);
    let offset = 0;

    function nextToken() {
      while (offset < view.length) {
        if (String.fromCharCode(view[offset]).match(/\s/)) offset++;
        else if (view[offset] === 35) { 
          while (offset < view.length && view[offset] !== 10) offset++;
        } else break;
      }
      if (offset >= view.length) return null;
      let token = "";
      while (offset < view.length && !String.fromCharCode(view[offset]).match(/\s/)) {
        token += String.fromCharCode(view[offset]);
        offset++;
      }
      return token;
    }

    const magic = nextToken();
    if (magic !== 'P5') return alert(i18n[lang].errPgmFormat);
    
    const imgWidth = parseInt(nextToken());
    const imgHeight = parseInt(nextToken());
    
    let char = String.fromCharCode(view[offset]);
    if (char === '\r') offset++;
    if (String.fromCharCode(view[offset]) === '\n') offset++;
    else if (char.match(/\s/)) offset++; 

    const canvas = document.createElement('canvas');
    canvas.width = imgWidth;
    canvas.height = imgHeight;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(imgWidth, imgHeight);

    for (let i = 0; i < imgWidth * imgHeight; i++) {
      const val = view[offset + i];
      const px = i * 4;
      imgData.data[px] = val;     
      imgData.data[px+1] = val;   
      imgData.data[px+2] = val;   
      imgData.data[px+3] = 255;   
    }
    ctx.putImageData(imgData, 0, 0);

    mapImageProps = {
      url: canvas.toDataURL(), 
      width: imgWidth,
      height: imgHeight,
      resolution,
      originX,
      originY,
      originYaw
    };
  }

  function handleSave(event, filename) {
    const updatedData = event.detail;
    if (updatedData.length === 0) {
      showToast(i18n[lang].errNoData);
      return;
    }
    
    const headers = Object.keys(updatedData[0]);
    
    const csvContent = headers.join(',') + '\n' + 
      updatedData.map(row => headers.map(h => {
        let val = row[h];
        if (typeof val === 'number') {
          if (h === 'id' || h === 'type') {
            return Math.round(val).toString();
          } else {
            return val.toFixed(2);
          }
        }
        return val;
      }).join(',')).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast(`${i18n[lang].successSave} ${filename}!`);
  }
</script>

<div class="map-editor-wrapper">
  <div class="top-bar">
    <div class="title-group">
      <h1>{i18n[lang].title}</h1>
      <button class="lang-toggle" on:click={toggleLanguage}>
        {lang === 'en' ? 'Language: 🇬🇧 EN' : 'Bahasa: 🇮🇩 ID' }
      </button>
    </div>
    
    <div class="upload-group">
      <div class="upload-item">
        <label>{i18n[lang].uploadMap}</label>
        <input type="file" multiple accept=".pgm, .yaml, .yml" on:change={handleMapUpload} />
      </div>
      <div class="upload-item">
        <label>{i18n[lang].uploadWp}</label>
        <input type="file" accept=".csv, .tsv, .txt" on:change={handleWaypointUpload} />
      </div>
      <div class="upload-item">
        <label>{i18n[lang].uploadTerm}</label>
        <input type="file" accept=".csv, .tsv, .txt" on:change={handleTerminalUpload} />
      </div>
    </div>
  </div>

  {#if mapData.length > 0 || terminalData.length > 0 || mapImageProps}
    <div class="tabs">
      <button class:active={activeTab === 'waypoint'} on:click={() => activeTab = 'waypoint'}>
        {i18n[lang].wpEditor}
      </button>
      <button class:active={activeTab === 'terminal'} on:click={() => activeTab = 'terminal'}>
        {i18n[lang].termEditor}
      </button>
    </div>

    <div class="editor-container">
      {#if activeTab === 'waypoint'}
        <!-- We pass 'lang' down as a prop in case you want to translate the child components later -->
        <WaypointEditor 
          {lang}
          waypoints={mapData} 
          mapImage={mapImageProps} 
          on:save={(e) => handleSave(e, waypointFileName)} 
        />
      {:else}
        <TerminalEditor 
          {lang}
          terminals={terminalData}
          waypoints={mapData} 
          mapImage={mapImageProps} 
          on:save={(e) => handleSave(e, terminalFileName)} 
        />
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <p>{i18n[lang].emptyState}</p>
    </div>
  {/if}
</div>

{#if toastMessage}
  <div class="toast-notification">
    {toastMessage}
  </div>
{/if}

<style>
  :global(#app), :global(body), :global(html) {
    max-width: 100vw !important;
    width: 100vw !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow-x: hidden;
  }

  .map-editor-wrapper { 
    padding: 15px 20px; 
    font-family: sans-serif; 
    width: 100vw; 
    height: 100vh;
    box-sizing: border-box; 
    display: flex;
    flex-direction: column;
    background-color: #1a1a1a; 
  }

  .top-bar { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    margin-bottom: 15px; 
    background: white; 
    padding: 15px 25px; 
    border-radius: 8px; 
    box-shadow: 0 2px 10px rgba(0,0,0,0.05); 
  }

  .title-group {
    display: flex;
    align-items: center;
    gap: 15px;
  }
  
  h1 { margin: 0; font-size: 22px; color: #333; }

  /* LANGUAGE TOGGLE BUTTON STYLES */
  .lang-toggle {
    background: #f1f3f5;
    border: 1px solid #ced4da;
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 14px;
    font-weight: bold;
    color: #495057;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .lang-toggle:hover {
    background: #e2e6ea;
    border-color: #adb5bd;
  }

  .upload-group { display: flex; gap: 20px; flex-wrap: wrap; }
  .upload-item { display: flex; flex-direction: column; gap: 5px; }
  .upload-item label { font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; }
  input[type="file"] { font-family: monospace; background: #eef1f5; padding: 8px; border-radius: 4px; cursor: pointer; border: 1px solid #ccc; max-width: 200px; }
  
  .tabs { display: flex; justify-content: flex-end; gap: 10px; margin-bottom: 15px; }
  .tabs button { padding: 10px 20px; font-size: 15px; font-weight: bold; border: none; background: #eef1f5; border-radius: 6px; cursor: pointer; transition: all 0.2s; color: #555; }
  .tabs button.active { background: #0064ff; color: white; box-shadow: 0 2px 8px rgba(0,100,255,0.3); }
  .tabs button:hover:not(.active) { background: #dfe4ea; }

  .empty-state { text-align: center; padding: 100px 20px; color: #888; background: white; border: 2px dashed #ccc; border-radius: 8px; font-size: 18px; margin-top: 10px; }
  
  .editor-container { flex: 1; min-height: 0; width: 100%; }

  .toast-notification {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background: #28a745;
    color: white;
    padding: 15px 25px;
    border-radius: 8px;
    font-family: sans-serif;
    font-weight: bold;
    font-size: 16px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    z-index: 9999;
    animation: slideIn 0.3s ease-out forwards, fadeOut 0.3s ease-in 2.7s forwards;
  }

  @keyframes slideIn {
    0% { transform: translateX(100%); opacity: 0; }
    100% { transform: translateX(0); opacity: 1; }
  }
  @keyframes fadeOut {
    0% { opacity: 1; }
    100% { opacity: 0; }
  }
</style>