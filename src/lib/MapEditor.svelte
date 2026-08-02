<script>
  import WaypointEditor from './WaypointEditor.svelte';
  import TerminalEditor from './TerminalEditor.svelte';

  let mapData = [];
  let terminalData = [];
  let mapImageProps = null; 
  let activeTab = 'waypoint';

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

  function handleWaypointUpload(event) { loadCsv(event.target.files[0], data => mapData = data); }
  function handleTerminalUpload(event) { loadCsv(event.target.files[0], data => terminalData = data); }

  async function handleMapUpload(event) {
    const files = event.target.files;
    let pgmFile = null;
    let yamlFile = null;

    for (let file of files) {
      if (file.name.toLowerCase().endsWith('.pgm')) pgmFile = file;
      if (file.name.toLowerCase().endsWith('.yaml') || file.name.toLowerCase().endsWith('.yml')) yamlFile = file;
    }

    if (!pgmFile || !yamlFile) return alert("⚠️ Please select BOTH the .pgm and .yaml/.yml files at the same time.");

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
    if (magic !== 'P5') return alert("Error: Only binary (P5) PGM files are supported.");
    
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
    if (updatedData.length === 0) return;
    const headers = Object.keys(updatedData[0]);
    const csvContent = headers.join(',') + '\n' + 
      updatedData.map(row => headers.map(h => typeof row[h] === 'number' ? row[h].toFixed(2) : row[h]).join(',')).join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<div class="map-editor-wrapper">
  <div class="top-bar">
    <h1>Map Configurator</h1>
    <div class="upload-group">
      <div class="upload-item">
        <label>Upload Map (.pgm & .yaml)</label>
        <input type="file" multiple accept=".pgm, .yaml, .yml" on:change={handleMapUpload} />
      </div>
      <div class="upload-item">
        <label>Upload Waypoints (CSV)</label>
        <input type="file" accept=".csv, .tsv, .txt" on:change={handleWaypointUpload} />
      </div>
      <div class="upload-item">
        <label>Upload Terminals (CSV)</label>
        <input type="file" accept=".csv, .tsv, .txt" on:change={handleTerminalUpload} />
      </div>
    </div>
  </div>

  {#if mapData.length > 0 || terminalData.length > 0 || mapImageProps}
    <div class="tabs">
      <button class:active={activeTab === 'waypoint'} on:click={() => activeTab = 'waypoint'}>📍 Waypoint Editor</button>
      <button class:active={activeTab === 'terminal'} on:click={() => activeTab = 'terminal'}>🎯 Terminal Editor</button>
    </div>

    <div class="editor-container">
      {#if activeTab === 'waypoint'}
        <WaypointEditor 
          waypoints={mapData} 
          mapImage={mapImageProps} 
          on:save={(e) => handleSave(e, 'edited_waypoints.csv')} 
        />
      {:else}
        <TerminalEditor 
          terminals={terminalData}
          waypoints={mapData} 
          mapImage={mapImageProps} 
          on:save={(e) => handleSave(e, 'edited_terminals.csv')} 
        />
      {/if}
    </div>
  {:else}
    <div class="empty-state">
      <p>📁 Please upload data or a Map image to begin editing.</p>
    </div>
  {/if}
</div>

<style>
  /* 🔥 OVERRIDE VITE DEFAULTS: Forces the app to span the entire screen */
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
    height: 100vh; /* Force full screen height */
    box-sizing: border-box; 
    display: flex;
    flex-direction: column;
    background-color: #1a1a1a; /* Matches the dark background of your browser */
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
  
  h1 { margin: 0; font-size: 22px; color: #333; }
  .upload-group { display: flex; gap: 20px; flex-wrap: wrap; }
  .upload-item { display: flex; flex-direction: column; gap: 5px; }
  .upload-item label { font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; }
  input[type="file"] { font-family: monospace; background: #eef1f5; padding: 8px; border-radius: 4px; cursor: pointer; border: 1px solid #ccc; max-width: 200px; }
  
  .tabs { display: flex; gap: 10px; margin-bottom: 15px; }
  .tabs button { padding: 10px 20px; font-size: 15px; font-weight: bold; border: none; background: #eef1f5; border-radius: 6px; cursor: pointer; transition: all 0.2s; color: #555; }
  .tabs button.active { background: #0064ff; color: white; box-shadow: 0 2px 8px rgba(0,100,255,0.3); }
  .tabs button:hover:not(.active) { background: #dfe4ea; }

  .empty-state { text-align: center; padding: 100px 20px; color: #888; background: white; border: 2px dashed #ccc; border-radius: 8px; font-size: 18px; margin-top: 10px; }
  
  .editor-container { 
    flex: 1; /* 🔥 Stretches the editor to fill the remaining bottom space */
    min-height: 0; /* Required for nested flexbox scrolling */
    width: 100%; 
  }
</style>