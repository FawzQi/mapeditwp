<script>
  import WaypointEditor from './WaypointEditor.svelte';

  let mapData = [];
  let mapImageProps = null; // Holds the parsed PGM and YAML data

  // --- 1. WAYPOINT CSV UPLOAD ---
  function handleCsvUpload(event) {
    const file = event.target.files[0];
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
      mapData = parsedData;
    };
    reader.readAsText(file);
  }

  // // --- 2. ROS MAP UPLOAD (PGM + YAML) ---
  // async function handleMapUpload(event) {
  //   const files = event.target.files;
  //   let pgmFile = null;
  //   let yamlFile = null;

  //   // Identify which file is which
  //   for (let file of files) {
  //     if (file.name.toLowerCase().endsWith('.pgm')) pgmFile = file;
  //     if (file.name.toLowerCase().endsWith('.yaml') || file.name.toLowerCase().endsWith('.yml')) yamlFile = file;
  //   }

  //   if (!pgmFile || !yamlFile) {
  //     alert("⚠️ Please select BOTH the .pgm and .yaml/.yml files at the same time.");
  //     return;
  //   }

  //   // Step A: Parse YAML to get real-world scale and origin
  //   const yamlText = await yamlFile.text();
  //   const resMatch = yamlText.match(/resolution:\s*([\d.]+)/);
  //   const originMatch = yamlText.match(/origin:\s*\[\s*([\d.-]+)\s*,\s*([\d.-]+)/);
    
  //   const resolution = resMatch ? parseFloat(resMatch[1]) : 0.05;
  //   const originX = originMatch ? parseFloat(originMatch[1]) : 0;
  //   const originY = originMatch ? parseFloat(originMatch[2]) : 0;

  //   // Step B: Parse PGM (P5 Binary format) into an HTML Canvas
  //   const buffer = await pgmFile.arrayBuffer();
  //   const view = new Uint8Array(buffer);
  //   let offset = 0;

  //   // Helper to read through PGM headers
  //   function nextToken() {
  //     while (offset < view.length) {
  //       if (String.fromCharCode(view[offset]).match(/\s/)) offset++;
  //       else if (view[offset] === 35) { // Skip '#' comments
  //         while (offset < view.length && view[offset] !== 10) offset++;
  //       } else break;
  //     }
  //     if (offset >= view.length) return null;
  //     let token = "";
  //     while (offset < view.length && !String.fromCharCode(view[offset]).match(/\s/)) {
  //       token += String.fromCharCode(view[offset]);
  //       offset++;
  //     }
  //     return token;
  //   }

  //   const magic = nextToken();
  //   if (magic !== 'P5') {
  //     alert("Error: Only binary (P5) PGM files are supported.");
  //     return;
  //   }
    
  //   const imgWidth = parseInt(nextToken());
  //   const imgHeight = parseInt(nextToken());
  //   const maxVal = parseInt(nextToken());
  //   offset++; // Skip single whitespace separating header from binary data

  //   // Draw raw pixels onto an off-screen canvas
  //   const canvas = document.createElement('canvas');
  //   canvas.width = imgWidth;
  //   canvas.height = imgHeight;
  //   const ctx = canvas.getContext('2d');
  //   const imgData = ctx.createImageData(imgWidth, imgHeight);

  //   for (let i = 0; i < imgWidth * imgHeight; i++) {
  //     const val = view[offset + i];
  //     const px = i * 4;
  //     imgData.data[px] = val;     // R
  //     imgData.data[px+1] = val;   // G
  //     imgData.data[px+2] = val;   // B
  //     imgData.data[px+3] = 255;   // Alpha
  //   }
  //   ctx.putImageData(imgData, 0, 0);

  //   // Save as state to pass into the Editor component
  //   mapImageProps = {
  //     url: canvas.toDataURL(), // Base64 image
  //     width: imgWidth,
  //     height: imgHeight,
  //     resolution,
  //     originX,
  //     originY
  //   };
  // }
  // --- 2. ROS MAP UPLOAD (PGM + YAML) ---
  async function handleMapUpload(event) {
    const files = event.target.files;
    let pgmFile = null;
    let yamlFile = null;

    for (let file of files) {
      if (file.name.toLowerCase().endsWith('.pgm')) pgmFile = file;
      if (file.name.toLowerCase().endsWith('.yaml') || file.name.toLowerCase().endsWith('.yml')) yamlFile = file;
    }

    if (!pgmFile || !yamlFile) {
      alert("⚠️ Please select BOTH the .pgm and .yaml/.yml files at the same time.");
      return;
    }

    // Step A: Parse YAML to get real-world scale, origin, and YAW (rotation)
    const yamlText = await yamlFile.text();
    const resMatch = yamlText.match(/resolution:\s*([\d.]+)/);
    
    // FIX: Match [x, y, yaw] to capture map rotation
    const originMatch = yamlText.match(/origin:\s*\[\s*([\d.-]+)\s*,\s*([\d.-]+)(?:\s*,\s*([\d.-]+))?/);
    
    const resolution = resMatch ? parseFloat(resMatch[1]) : 0.05;
    const originX = originMatch ? parseFloat(originMatch[1]) : 0;
    const originY = originMatch ? parseFloat(originMatch[2]) : 0;
    const originYaw = (originMatch && originMatch[3]) ? parseFloat(originMatch[3]) : 0;

    // Step B: Parse PGM (P5 Binary format) into an HTML Canvas
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
    if (magic !== 'P5') {
      alert("Error: Only binary (P5) PGM files are supported.");
      return;
    }
    
    const imgWidth = parseInt(nextToken());
    const imgHeight = parseInt(nextToken());
    const maxVal = parseInt(nextToken());
    
    // FIX: Safely skip the single whitespace to prevent 1-byte diagonal skewing
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

    // Save as state and pass the newly extracted Yaw
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

  // --- 3. EXPORTING BACK TO CSV ---
  function handleSave(event) {
    const updatedData = event.detail;
    if (updatedData.length === 0) return;
    const headers = Object.keys(updatedData[0]);
    const csvContent = headers.join(',') + '\n' + 
      updatedData.map(row => headers.map(h => row[h]).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'edited_waypoints.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
</script>

<main>
  <div class="top-bar">
    <h1>Map Editor</h1>
    <div class="upload-group">
      <div class="upload-item">
        <label>1. Upload Waypoints (CSV)</label>
        <input type="file" accept=".csv, .tsv, .txt" on:change={handleCsvUpload} />
      </div>
      <div class="upload-item">
        <label>2. Upload Map (.pgm & .yaml)</label>
        <input type="file" multiple accept=".pgm, .yaml, .yml" on:change={handleMapUpload} />
      </div>
    </div>
  </div>

  {#if mapData.length > 0 || mapImageProps}
    <div class="editor-container">
      <WaypointEditor 
        waypoints={mapData} 
        mapImage={mapImageProps} 
        on:save={handleSave} 
      />
    </div>
  {:else}
    <div class="empty-state">
      <p>📁 Please upload Waypoints or a Map image to begin editing.</p>
    </div>
  {/if}
</main>

<style>
  :global(body) { margin: 0; padding: 0; background-color: #f4f4f9; }
  main { padding: 20px; font-family: sans-serif; max-width: 95%; margin: 100 auto; }
  .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; background: white; padding: 15px 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
  h1 { margin: 0; font-size: 22px; color: #333; }
  .upload-group { display: flex; gap: 20px; }
  .upload-item { display: flex; flex-direction: column; gap: 5px; }
  .upload-item label { font-size: 12px; font-weight: bold; color: #666; text-transform: uppercase; }
  input[type="file"] { font-family: monospace; background: #eef1f5; padding: 8px; border-radius: 4px; cursor: pointer; border: 1px solid #ccc; }
  .empty-state { text-align: center; padding: 100px 20px; color: #888; background: white; border: 2px dashed #ccc; border-radius: 8px; font-size: 18px; }
  .editor-container { background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
</style>