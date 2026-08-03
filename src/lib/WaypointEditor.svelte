<script>
  import { createEventDispatcher } from 'svelte';
  
  export let waypoints = []; 
  export let mapImage = null;
  export let lang = 'en';

  const i18n = {
    en: {
      howToUse: "📖 How to Use",
      mouseControls: "Mouse Controls",
      labelLeftClick: "Left Click",
      leftClick: "Select & move points.",
      labelRightDrag: "Right Drag",
      rightDrag: "Pan the map view.",
      labelDoubleClick: "Double-Click",
      doubleClick: "Auto-fit bounds/Zoom out.",
      selection: "Selection",
      labelDragEmpty: "Drag empty space",
      dragEmpty: "Select multiple points inside a box.",
      labelAltClick: "Alt + Click",
      altClick: "Multi-select or deselect individual points.",
      shortcuts: "Shortcuts",
      shortcutEdit: "Edit Mode",
      shortcutZoom: "Zoom Mode",
      shortcutUndo: "Undo",
      shortcutSave: "Save",
      shortcutDelete: "Remove Selected",
      transformations: "Transformations",
      transformDesc: "Use the WP Transform tools to align the trajectory. Click <b>Auto-Align</b> to estimate based on map pixel dimensions, or set values manually. Click <b>Apply</b> to bake coordinates.",
      errUploadMapFirst: "Please upload a Map (.pgm & .yaml) first.",

      tools: "Tools",
      editMode: "Edit (Alt+E)",
      zoomMode: "Zoom (Alt+X)",
      modifySelection: "Modify Selection",
      rotateClockwise: "rotate ↺",
      rotateCounterClockwise: "↻ rotate",
      titleRotateCw: "Rotate Clockwise",
      titleRotateCcw: "Rotate Counter-Clockwise",
      deleteSelected: "Delete (Del)",
      wpTransform: "WP Transform",
      labelScale: "Scale",
      autoAlign: "Auto-Align",
      applyToPoints: "Apply to Points",
      actions: "Actions",
      undo: "Undo (Alt+Z)",
      saveMap: "Save Map"
    },
    id: {
      howToUse: "📖 Cara Penggunaan",
      mouseControls: "Kontrol Mouse",
      labelLeftClick: "Klik Kiri",
      leftClick: "Pilih & pindahkan titik.",
      labelRightDrag: "Geser Kanan",
      rightDrag: "Geser tampilan peta.",
      labelDoubleClick: "Klik Ganda",
      doubleClick: "Sesuaikan tampilan otomatis / Zoom out.",
      selection: "Pilihan",
      labelDragEmpty: "Seret area kosong",
      dragEmpty: "Pilih banyak titik di dalam kotak.",
      labelAltClick: "Alt + Klik",
      altClick: "Pilih / batal pilih beberapa titik secara individual.",
      shortcuts: "Pintasan",
      shortcutEdit: "Mode Edit",
      shortcutZoom: "Mode Pembesaran",
      shortcutUndo: "Batalkan",
      shortcutSave: "Simpan",
      shortcutDelete: "Hapus Yang Dipilih",
      transformations: "Transformasi",
      transformDesc: "Gunakan alat Transformasi WP untuk menyelaraskan lintasan. Klik <b>Auto-Align</b> untuk mengestimasi berdasarkan dimensi piksel peta, atau atur nilai secara manual. Klik <b>Terapkan ke Titik</b> untuk mengaplikasikan koordinat.",
      errUploadMapFirst: "Silakan unggah Peta (.pgm & .yaml) terlebih dahulu.",

      tools: "Alat",
      editMode: "Edit (Alt+E)",
      zoomMode: "Pembesaran (Alt+X)",
      modifySelection: "Ubah Pilihan",
      rotateClockwise: "putar ↺",
      rotateCounterClockwise: "↻ putar",
      titleRotateCw: "Putar Searah Jarum Jam",
      titleRotateCcw: "Putar Berlawanan Jarum Jam",
      deleteSelected: "Hapus (Del)",
      wpTransform: "Transformasi WP",
      labelScale: "Skala",
      autoAlign: "Ratakan Otomatis",
      applyToPoints: "Terapkan ke Titik",
      actions: "Aksi",
      undo: "Batalkan (Alt+Z)",
      saveMap: "Simpan Peta"
    }
  };

  const dispatch = createEventDispatcher();

  let editMode = 'edit';
  let dragAction = 'none'; 
  
  let selectedIdxs = new Set();
  let undoStack = [];
  
  let customView = null;
  let zoomUndoStack = [];
  
  let wpOriginX = 0;
  let wpOriginY = 0;
  let wpOriginYaw = 0; 
  let wpScale = 1.0; 
  $: safeScale = wpScale === 0 ? 0.0001 : wpScale; 
  
  let dragStartPos = null;
  let panStartPixel = null;
  let rectStart = null;
  let rectCurrent = null;
  
  let svgElement;
  let dataLayer; 
  let wpLayer;   
  let svgWidth = 800;
  let svgHeight = 600;

  const saveState = () => undoStack.push({
    waypoints: JSON.parse(JSON.stringify(waypoints)),
    wpOriginX, wpOriginY, wpOriginYaw, wpScale
  });

  function undoLastMove() { 
    if (undoStack.length > 0) {
      const state = undoStack.pop();
      waypoints = state.waypoints;
      wpOriginX = state.wpOriginX;
      wpOriginY = state.wpOriginY;
      wpOriginYaw = state.wpOriginYaw;
      wpScale = state.wpScale || 1.0;
      selectedIdxs = new Set();
    }
  }

  function lockView() { if (!customView) customView = { minX: activeMinX, maxX: activeMaxX, minY: activeMinY, maxY: activeMaxY }; }
  function resetZoom() { customView = zoomUndoStack.length > 0 ? zoomUndoStack.pop() : null; }
  function setMode(mode) { editMode = mode; }

  function deleteSelectedPoints() {
    if (selectedIdxs.size === 0) return;
    saveState(); 
    waypoints = waypoints.filter((_, i) => !selectedIdxs.has(i));
    selectedIdxs = new Set();
  }

  function rotateSelected(angleDegrees) {
    if (selectedIdxs.size === 0) return;
    saveState();
    
    const angleRad = angleDegrees * (Math.PI / 180);
    const cosA = Math.cos(angleRad);
    const sinA = Math.sin(angleRad);
    
    let cx = 0, cy = 0;
    for (let i of selectedIdxs) { cx += waypoints[i].x; cy += waypoints[i].y; }
    cx /= selectedIdxs.size; cy /= selectedIdxs.size;
    
    waypoints = waypoints.map((wp, i) => {
      if (selectedIdxs.has(i)) {
        const dx = wp.x - cx; const dy = wp.y - cy;
        return { ...wp, x: cx + (dx * cosA - dy * sinA), y: cy + (dx * sinA + dy * cosA) };
      }
      return wp;
    });
  }

  function autoAlignMap() {
    if (!mapImage) return alert(i18n[lang].errUploadMapFirst);
    const w = mapImage.width;
    const h = mapImage.height;
    
    let calcX = 0.5 + ((w - 779) / 75) * 1.0;
    let calcY = 0.0 + ((h - 282) / 120) * 0.7;
    let calcYaw = 0.0095 + ((w - 779) / 75) * -0.0295;
    
    wpOriginX = parseFloat(calcX.toFixed(3));
    wpOriginY = parseFloat(calcY.toFixed(3));
    wpOriginYaw = parseFloat(calcYaw.toFixed(4));
    wpScale = mapImage.resolution;
  }

  function bakeTransform() {
    saveState();
    waypoints = waypoints.map(w => {
      const sx = w.x * safeScale;
      const sy = w.y * safeScale;
      const cosT = Math.cos(wpOriginYaw);
      const sinT = Math.sin(wpOriginYaw);
      return { ...w, x: sx * cosT - sy * sinT + wpOriginX, y: sx * sinT + sy * cosT + wpOriginY };
    });
    wpOriginX = 0; wpOriginY = 0; wpOriginYaw = 0; wpScale = 1.0;
  }

  function onKey(event) {
    const key = event.key.toLowerCase();
    if (event.altKey && key === 's') dispatch('save', waypoints);
    else if (event.altKey && key === 'z') { editMode === 'zoom' ? resetZoom() : undoLastMove(); } 
    else if (event.altKey && key === 'e') setMode('edit');
    else if (event.altKey && key === 'x') setMode('zoom');
    else if (key === 'delete' || key === 'backspace') deleteSelectedPoints(); 
  }

  function getGlobalCoords(event) {
    if (!dataLayer) return { x: 0, y: 0 };
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX; pt.y = event.clientY;
    const svgP = pt.matrixTransform(dataLayer.getScreenCTM().inverse());
    return { x: svgP.x, y: svgP.y };
  }

  function getLocalCoords(event) {
    if (!wpLayer) return { x: 0, y: 0 };
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX; pt.y = event.clientY;
    const svgP = pt.matrixTransform(wpLayer.getScreenCTM().inverse());
    return { x: svgP.x, y: svgP.y };
  }

  function onPress(event) {
    if (event.button === 2) {
      dragAction = 'pan';
      panStartPixel = { x: event.clientX, y: event.clientY };
      lockView(); 
      return; 
    }

    const coords = (editMode === 'zoom') ? getGlobalCoords(event) : getLocalCoords(event);
    dragStartPos = coords;

    if (editMode === 'edit') {
      let closestIdx = -1;
      let minDist = Infinity;
      const clickThreshold = (pointRadius * 4.0) / safeScale; 
      
      waypoints.forEach((wp, i) => {
        const dist = Math.sqrt(Math.pow(wp.x - coords.x, 2) + Math.pow(wp.y - coords.y, 2));
        if (dist < minDist && dist < clickThreshold) { minDist = dist; closestIdx = i; }
      });

      if (closestIdx !== -1) {
        if (event.altKey) {
          if (selectedIdxs.has(closestIdx)) selectedIdxs.delete(closestIdx);
          else selectedIdxs.add(closestIdx);
          selectedIdxs = selectedIdxs; 
        } else if (!selectedIdxs.has(closestIdx)) {
          selectedIdxs = new Set([closestIdx]); 
        }
        dragAction = 'move';
        saveState(); lockView();
      } else {
        selectedIdxs = new Set(); 
        dragAction = 'rect';
        rectStart = coords; rectCurrent = coords;
      }
    } 
    else if (editMode === 'zoom') {
      dragAction = 'zoomRect';
      rectStart = coords; rectCurrent = coords;
    }
  }

  function onMotion(event) {
    if (dragAction === 'pan' && panStartPixel) {
      const dxPixels = event.clientX - panStartPixel.x;
      const dyPixels = event.clientY - panStartPixel.y;
      const dxData = dxPixels * (activeRangeX / svgWidth);
      const dyData = dyPixels * (activeRangeY / svgHeight);

      customView = {
        minX: customView.minX - dxData, maxX: customView.maxX - dxData,
        minY: customView.minY + dyData, maxY: customView.maxY + dyData
      };
      panStartPixel = { x: event.clientX, y: event.clientY };
      return;
    }

    if (dragAction === 'none' || !dragStartPos) return;
    
    const coords = (editMode === 'zoom') ? getGlobalCoords(event) : getLocalCoords(event);
    const dx = coords.x - dragStartPos.x;
    const dy = coords.y - dragStartPos.y;

    if (dragAction === 'move' && selectedIdxs.size > 0) {
      for (let i of selectedIdxs) { waypoints[i].x += dx; waypoints[i].y += dy; }
      dragStartPos = coords; waypoints = waypoints; 
    } else if (dragAction === 'rect' || dragAction === 'zoomRect') {
      rectCurrent = coords;
    }
  }

  function onRelease() {
    if (dragAction === 'pan') { panStartPixel = null; }
    
    if ((dragAction === 'rect' || dragAction === 'zoomRect') && rectStart && rectCurrent) {
      const xMin = Math.min(rectStart.x, rectCurrent.x); const xMax = Math.max(rectStart.x, rectCurrent.x);
      const yMin = Math.min(rectStart.y, rectCurrent.y); const yMax = Math.max(rectStart.y, rectCurrent.y);

      if (dragAction === 'rect') {
        const newSelection = new Set();
        waypoints.forEach((wp, i) => { if (wp.x >= xMin && wp.x <= xMax && wp.y >= yMin && wp.y <= yMax) newSelection.add(i); });
        selectedIdxs = newSelection;
      } else if (dragAction === 'zoomRect') {
        if (xMax - xMin > activeRangeX * 0.02 && yMax - yMin > activeRangeY * 0.02) {
          zoomUndoStack.push(customView ? { ...customView } : null);
          customView = { minX: xMin, maxX: xMax, minY: yMin, maxY: yMax };
        }
        editMode = 'edit'; 
      }
      rectStart = null; rectCurrent = null;
    }
    dragAction = 'none'; dragStartPos = null; 
  }
  
  $: transformedWaypoints = waypoints.map(w => {
    const sx = w.x * safeScale;
    const sy = w.y * safeScale;
    const cosT = Math.cos(wpOriginYaw);
    const sinT = Math.sin(wpOriginYaw);
    return { x: sx * cosT - sy * sinT + wpOriginX, y: sx * sinT + sy * cosT + wpOriginY };
  });

  $: wpMinX = transformedWaypoints.length ? Math.min(...transformedWaypoints.map(w => w.x)) : Infinity;
  $: wpMaxX = transformedWaypoints.length ? Math.max(...transformedWaypoints.map(w => w.x)) : -Infinity;
  $: wpMinY = transformedWaypoints.length ? Math.min(...transformedWaypoints.map(w => w.y)) : Infinity;
  $: wpMaxY = transformedWaypoints.length ? Math.max(...transformedWaypoints.map(w => w.y)) : -Infinity;

  $: mapMinX = mapImage ? mapImage.originX : Infinity;
  $: mapMaxX = mapImage ? mapImage.originX + (mapImage.width * mapImage.resolution) : -Infinity;
  $: mapMinY = mapImage ? mapImage.originY : Infinity;
  $: mapMaxY = mapImage ? mapImage.originY + (mapImage.height * mapImage.resolution) : -Infinity;

  $: rawMinX = Math.min(wpMinX, mapMinX) === Infinity ? 0 : Math.min(wpMinX, mapMinX);
  $: rawMaxX = Math.max(wpMaxX, mapMaxX) === -Infinity ? 10 : Math.max(wpMaxX, mapMaxX);
  $: rawMinY = Math.min(wpMinY, mapMinY) === Infinity ? 0 : Math.min(wpMinY, mapMinY);
  $: rawMaxY = Math.max(wpMaxY, mapMaxY) === -Infinity ? 10 : Math.max(wpMaxY, mapMaxY);
  
  $: rangeX = Math.max(rawMaxX - rawMinX, 1);
  $: rangeY = Math.max(rawMaxY - rawMinY, 1);
  $: paddedMinX = rawMinX - (rangeX * 0.1);
  $: paddedMaxX = rawMaxX + (rangeX * 0.1);
  $: paddedMinY = rawMinY - (rangeY * 0.1);
  $: paddedMaxY = rawMaxY + (rangeY * 0.1);

  $: targetMinX = customView ? customView.minX : paddedMinX;
  $: targetMaxX = customView ? customView.maxX : paddedMaxX;
  $: targetMinY = customView ? customView.minY : paddedMinY;
  $: targetMaxY = customView ? customView.maxY : paddedMaxY;

  $: targetRangeX = Math.max(targetMaxX - targetMinX, 0.0001);
  $: targetRangeY = Math.max(targetMaxY - targetMinY, 0.0001);
  $: targetCenterX = targetMinX + targetRangeX / 2;
  $: targetCenterY = targetMinY + targetRangeY / 2;

  $: targetRatio = targetRangeX / targetRangeY;
  $: currentSvgRatio = Math.max(svgWidth, 1) / Math.max(svgHeight, 1);

  $: activeRangeX = currentSvgRatio > targetRatio ? targetRangeY * currentSvgRatio : targetRangeX;
  $: activeRangeY = currentSvgRatio > targetRatio ? targetRangeY : targetRangeX / currentSvgRatio;

  $: activeMinX = targetCenterX - activeRangeX / 2;
  $: activeMaxX = targetCenterX + activeRangeX / 2;
  $: activeMinY = targetCenterY - activeRangeY / 2;
  $: activeMaxY = targetCenterY + activeRangeY / 2;

  $: pxScale = activeRangeX / Math.max(svgWidth, 1);
  $: gridStroke = 1 * pxScale;
  $: lineStroke = 5 * pxScale; 
  $: pointRadius = 3 * pxScale;
  $: fontSize = 14 * pxScale;
  
  function calculateTickStep(min, max, maxTicks) {
    const range = max - min;
    if (range <= 0) return 1;
    const rawStep = range / maxTicks;
    const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
    const normalized = rawStep / magnitude;
    if (normalized <= 1) return 1 * magnitude;
    if (normalized <= 2) return 2 * magnitude;
    if (normalized <= 5) return 5 * magnitude;
    return 10 * magnitude;
  }

  $: stepX = calculateTickStep(activeMinX, activeMaxX, 10);
  $: stepY = calculateTickStep(activeMinY, activeMaxY, 8);

  $: startX = Math.floor(activeMinX / stepX) * stepX;
  $: xTicks = Array.from({ length: Math.ceil((activeMaxX - activeMinX) / stepX) + 2 }, (_, i) => startX + (i * stepX));
  $: startY = Math.floor(activeMinY / stepY) * stepY;
  $: yTicks = Array.from({ length: Math.ceil((activeMaxY - activeMinY) / stepY) + 2 }, (_, i) => startY + (i * stepY));

  const formatTick = (val) => parseFloat(val.toFixed(5));
  $: pointsString = waypoints.map(w => `${w.x},${w.y}`).join(' ');
</script>

<svelte:window on:keydown={onKey} />

<div class="editor-layout">

  <!-- LEFT: INSTRUCTION PANEL -->
  <div class="info-panel">
    <h3>{i18n[lang].howToUse}</h3>
    <div class="info-section">
      <h4>{i18n[lang].mouseControls}</h4>
      <ul>
        <li><strong>{i18n[lang].labelLeftClick}:</strong> {i18n[lang].leftClick}</li>
        <li><strong>{i18n[lang].labelRightDrag}:</strong> {i18n[lang].rightDrag}</li>
        <li><strong>{i18n[lang].labelDoubleClick}:</strong> {i18n[lang].doubleClick}</li>
      </ul>
    </div>
    <div class="info-section">
      <h4>{i18n[lang].selection}</h4>
      <ul>
        <li><strong>{i18n[lang].labelDragEmpty}:</strong> {i18n[lang].dragEmpty}</li>
        <li><strong>{i18n[lang].labelAltClick}:</strong> {i18n[lang].altClick}</li>
      </ul>
    </div>
    <div class="info-section">
      <h4>{i18n[lang].shortcuts}</h4>
      <ul>
        <li><strong>Alt + E:</strong> {i18n[lang].shortcutEdit}</li>
        <li><strong>Alt + X:</strong> {i18n[lang].shortcutZoom}</li>
        <li><strong>Alt + Z:</strong> {i18n[lang].shortcutUndo}</li>
        <li><strong>Alt + S:</strong> {i18n[lang].shortcutSave}</li>
        <li><strong>Delete:</strong> {i18n[lang].shortcutDelete}</li>
      </ul>
    </div>
    <div class="info-section">
      <h4>{i18n[lang].transformations}</h4>
      <p style="margin-top: 5px;">{@html i18n[lang].transformDesc}</p>
    </div>
  </div>

  <!-- CENTER: MAP RENDERING -->
  <div class="map-container">
    <svg 
      role="application"
      aria-label="Map Editor"
      bind:this={svgElement} bind:clientWidth={svgWidth} bind:clientHeight={svgHeight}
      viewBox="{activeMinX} {-activeMaxY} {activeRangeX} {activeRangeY}"
      preserveAspectRatio="none"
      on:mousedown={onPress} on:mousemove={onMotion} on:mouseup={onRelease} on:mouseleave={onRelease}
      on:dblclick={resetZoom} on:contextmenu|preventDefault 
    >
      <g bind:this={dataLayer} transform="scale(1, -1)">
        {#if mapImage}
          <g transform="rotate({(mapImage.originYaw) * 180 / Math.PI}) translate({mapImage.originX}, {mapImage.originY}) translate(0, {mapImage.height * mapImage.resolution}) scale(1, -1)">
            <image x="0" y="0" width={mapImage.width * mapImage.resolution} height={mapImage.height * mapImage.resolution} href={mapImage.url} preserveAspectRatio="none" />
          </g>
        {/if}

        {#if rectStart && rectCurrent && dragAction === 'zoomRect'}
          <rect x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)} width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)} fill="rgba(0, 100, 255, 0.15)" stroke="blue" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}" />
        {/if}

        <g bind:this={wpLayer} transform="translate({0+wpOriginX}, {0+wpOriginY}) rotate({(0+wpOriginYaw) * 180 / Math.PI}) scale({safeScale})">
          <polyline points={pointsString} fill="none" stroke="rgba(0, 0, 255, 0.4)" stroke-width={lineStroke / safeScale} />
         {#each waypoints as wp, i}
  <circle 
    cx={wp.x} cy={wp.y} 
    r={Math.max(pointRadius / safeScale, 0.05 / safeScale)} 
    fill={selectedIdxs.has(i) ? "red" : "#0064ff"} 
    class="hoverable-point" 
  />
{/each}
          {#if rectStart && rectCurrent && dragAction === 'rect'}
            <rect x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)} width={Math.abs(rectStart.x - rectCurrent.x)} height={Math.abs(rectCurrent.y - rectStart.y)} fill="rgba(0, 200, 0, 0.1)" stroke="green" stroke-width={lineStroke / safeScale} stroke-dasharray="{(lineStroke * 2) / safeScale}, {(lineStroke * 2) / safeScale}" />
          {/if}
        </g>
      </g>

      <g class="grid-system">
        {#each xTicks as x}
          <line x1={x} y1={-activeMaxY} x2={x} y2={-activeMinY} stroke="rgba(200,200,200,0.5)" stroke-width={gridStroke} />
          <text x={x} y={-activeMinY - (fontSize * 0.5)} font-size={fontSize} fill="#555" text-anchor="middle" paint-order="stroke" stroke="white" stroke-width={pxScale * 4}>{formatTick(x)}</text>
        {/each}
        {#each yTicks as y}
          <line x1={activeMinX} y1={-y} x2={activeMaxX} y2={-y} stroke="rgba(200,200,200,0.5)" stroke-width={gridStroke} />
          <text x={activeMinX + (fontSize * 0.5)} y={-y + (fontSize * 0.3)} font-size={fontSize} fill="#555" text-anchor="start" paint-order="stroke" stroke="white" stroke-width={pxScale * 4}>{formatTick(y)}</text>
        {/each}
      </g>
    </svg>
  </div>

  <!-- RIGHT: TOOLBAR -->
  <div class="toolbar">
    <h3>{i18n[lang].tools}</h3>
    <button class:active={editMode === 'edit'} on:click={() => setMode('edit')}><span>👆</span> {i18n[lang].editMode}</button>
    <button class:active={editMode === 'zoom'} on:click={() => setMode('zoom')}><span>🔍</span> {i18n[lang].zoomMode}</button>
    
    <div class="spacer"></div>

    <h3>{i18n[lang].modifySelection}</h3>
    <div class="btn-row">
      <button class="icon-btn" on:click={() => rotateSelected(2)} disabled={selectedIdxs.size === 0} title={i18n[lang].titleRotateCw}><span>{i18n[lang].rotateClockwise}</span></button>
      <button class="icon-btn" on:click={() => rotateSelected(-2)} disabled={selectedIdxs.size === 0} title={i18n[lang].titleRotateCcw}><span>{i18n[lang].rotateCounterClockwise}</span></button>
    </div>
    <button class="delete-btn" on:click={deleteSelectedPoints} disabled={selectedIdxs.size === 0}><span>🗑️</span> {i18n[lang].deleteSelected}</button>

    <div class="spacer"></div>

    <h3>{i18n[lang].wpTransform}</h3>
    <div class="origin-inputs">
      <label>X: <input type="number" step="0.5" bind:value={wpOriginX}></label>
      <label>Y: <input type="number" step="0.5" bind:value={wpOriginY}></label>
      <label>Yaw: <input type="number" step="0.01" bind:value={wpOriginYaw}></label>
      <label>{i18n[lang].labelScale}: <input type="number" step="0.01" bind:value={wpScale}></label>
      <button class="sync-btn" on:click={autoAlignMap}>{i18n[lang].autoAlign}</button>
      <button class="bake-btn" on:click={bakeTransform}>{i18n[lang].applyToPoints}</button>
    </div>

    <div class="spacer"></div>

    <h3>{i18n[lang].actions}</h3>
    <button class="action-btn" on:click={undoLastMove}><span>↩️</span> {i18n[lang].undo}</button>
    <button class="save-btn" on:click={() => dispatch('save', waypoints)}><span>💾</span> {i18n[lang].saveMap}</button>
  </div>
</div>

<style>
 /* Change this first line in your <style> block */
  .editor-layout { display: flex; flex-direction: row; gap: 15px; height: 100%; width: 100%; font-family: sans-serif; box-sizing: border-box; }
  /* Left Panel */
  .info-panel { width: 250px; flex-shrink: 0; display: flex; flex-direction: column; gap: 15px; background: #f9f9f9; padding: 15px; border-radius: 6px; border: 1px solid #ccc; overflow-y: auto; }
  .info-panel h3 { margin: 0; font-size: 16px; color: #333; border-bottom: 2px solid #ddd; padding-bottom: 8px;}
  .info-section { font-size: 13px; color: #555; line-height: 1.5; }
  .info-section h4 { margin: 0 0 5px 0; font-size: 13px; color: #0064ff; text-transform: uppercase; }
  .info-section ul { margin: 0; padding-left: 20px; }

  /* Center */
  .map-container { flex: 1; min-width: 0; position: relative; border: 1px solid #ccc; border-radius: 6px; overflow: hidden; background: #ffffff; background-image: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%); background-size: 20px 20px; background-position: 0 0, 0 10px, 10px -10px, -10px 0px; }
  
  /* Right Panel */
  .toolbar { width: 250px; flex-shrink: 0; display: flex; flex-direction: column; gap: 8px; background: #f9f9f9; padding: 15px; border-radius: 6px; border: 1px solid #ccc; overflow-y: auto; }
  .toolbar h3 { margin: 0 0 2px 0; font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .spacer { flex-grow: 1; min-height: 10px; }
  
  /* Shared Elements */
  .hoverable-point:hover { fill: rgba(0, 0, 255, 0.3) !important; cursor: grab; }
  svg { width: 100%; height: 100%; cursor: crosshair; user-select: none; display: block; }
  .grid-system text { font-family: sans-serif; font-weight: bold; pointer-events: none; }
  .btn-row { display: flex; gap: 6px; }
  .icon-btn { flex: 1; justify-content: center; padding: 10px 5px; }

  button { display: flex; align-items: center; gap: 8px; padding: 10px; font-size: 14px; text-align: left; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; transition: all 0.2s; color: #333; }
  button:hover:not(:disabled) { background: #f0f0f0; border-color: #bbb; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.active { background: #e0edff; border-color: #0064ff; color: #004dc4; font-weight: bold; }
  
  .delete-btn { background: #ffebee; border-color: #ef9a9a; color: #c62828; }
  .delete-btn:hover:not(:disabled) { background: #ffcdd2; }
  .action-btn { background: #fff3e0; border-color: #ffcc80; }
  .action-btn:hover { background: #ffe0b2; }
  .save-btn { background: #e8f5e9; border-color: #a5d6a7; font-weight: bold; }
  .save-btn:hover { background: #c8e6c9; }

  .origin-inputs { display: flex; flex-direction: column; gap: 6px; background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
  .origin-inputs label { display: flex; justify-content: space-between; align-items: center; font-weight: 600; color: #444; }
  .origin-inputs input { width: 80px; padding: 4px; font-family: monospace; border: 1px solid #ccc; border-radius: 3px; }
  .sync-btn { margin-top: 4px; justify-content: center; background: #f3e5f5; border-color: #ce93d8; color: #6a1b9a; font-weight: bold; padding: 6px; }
  .sync-btn:hover { background: #e1bee7; }
  .bake-btn { justify-content: center; background: #e3f2fd; border-color: #90caf9; color: #1565c0; font-weight: bold; padding: 6px; }
  .bake-btn:hover { background: #bbdefb; }
</style>