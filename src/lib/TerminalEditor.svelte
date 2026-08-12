<script>
  import { createEventDispatcher } from 'svelte';
  
  export let terminals = []; 
  export let waypoints = []; // Read-only visual context
  export let mapImage = null;
  export let lang = 'en';

  const i18n = {
    en: {
      howToUse: "📖 How to Use",
      mouseControls: "Basic Controls",
      labelLeftClick: "Move Terminals",
      leftClick: "Left-click & drag selected terminals.",
      labelRightDrag: "Pan Map",
      rightDrag: "Right-click & drag on empty space.",
      labelRotate: "Rotate",
      rotateDesc: "Select terminals, then right-click & drag on one of them.",
      labelDoubleClick: "Reset View",
      doubleClick: "Double-click to reset zoom.",
      selection: "Selection Tools",
      labelDragEmpty: "Box Select",
      dragEmpty: "Left-click & drag on empty space.",
      labelAltClick: "Multi-Select",
      altClick: "Alt + Left-click to add/remove terminals.",
      addingModifying: "Adding & Properties",
      labelAdd: "Add New",
      addDesc: "Click the ➕ tool and click the map.",
      labelProperties: "Edit Stats",
      propDesc: "Select <b>exactly one</b> terminal to edit its Type, Speed, and lookahead.",
      types: "Types",
      type1: "Type 1: Stop Area",
      type2: "Type 2: Slow Area",
      type32: "Type 32: Fast Area",

      tools: "Tools",
      selectEdit: "Select/Edit",
      addTerminal: "Add Terminal",
      zoom: "Zoom",
      modifySelection: "Modify Selection",
      deleteSelected: "Delete Selected",
      terminalId: "Terminal ID",
      terminalsSelected: "Terminals Selected",
      selectSinglePrompt: "Select a single terminal to edit its individual attributes.",
      typeLabel: "Type",
      radiusArea: "Radius",
      thetaRad: "Theta",
      maxVx: "Max Vx",
      maxVy: "Max Vy",
      maxVtheta: "Max Vθ",
      lookAhead: "LookAhead",
      obsScanR: "Obs Scan R",
      icpScoreMax: "ICP Max",
      scanMinX: "Scan Min X",
      scanMaxX: "Scan Max X",
      scanMinY: "Scan Min Y",
      scanMaxY: "Scan Max Y",
      obsThreshold: "Obs Thresh",
      actions: "Actions",
      undoAction: "Undo Action",
      saveTerminals: "Save Terminals"
    },
    id: {
      howToUse: "📖 Cara Penggunaan",
      mouseControls: "Kontrol Dasar",
      labelLeftClick: "Pindah Terminal",
      leftClick: "Klik kiri & seret terminal terpilih.",
      labelRightDrag: "Geser Peta",
      rightDrag: "Klik kanan & seret di area kosong.",
      labelRotate: "Putar Terminal",
      rotateDesc: "Pilih terminal, lalu klik kanan & seret pada terminal tersebut.",
      labelDoubleClick: "Reset Tampilan",
      doubleClick: "Klik ganda untuk reset zoom.",
      selection: "Alat Pilihan",
      labelDragEmpty: "Pilih Kotak",
      dragEmpty: "Klik kiri & seret di area kosong.",
      labelAltClick: "Pilih Banyak",
      altClick: "Alt + Klik kiri untuk tambah/hapus terminal.",
      addingModifying: "Menambah & Properti",
      labelAdd: "Tambah Baru",
      addDesc: "Pilih alat ➕ dan klik pada peta.",
      labelProperties: "Edit Atribut",
      propDesc: "Pilih <b>tepat satu</b> terminal untuk mengubah Tipe dan kecepatannya.",
      types: "Tipe Terminal",
      type1: "Tipe 1: Area Berhenti",
      type2: "Tipe 2: Area Lambat",
      type32: "Tipe 32: Area Cepat",

      tools: "Alat",
      selectEdit: "Pilih/Edit",
      addTerminal: "Tambah Terminal",
      zoom: "Pembesaran",
      modifySelection: "Ubah Pilihan",
      deleteSelected: "Hapus Yang Dipilih",
      terminalId: "ID Terminal",
      terminalsSelected: "Terminal Dipilih",
      selectSinglePrompt: "Pilih satu terminal untuk mengedit atributnya.",
      typeLabel: "Tipe",
      radiusArea: "Radius",
      thetaRad: "Theta",
      maxVx: "Vx Maks",
      maxVy: "Vy Maks",
      maxVtheta: "Vθ Maks",
      lookAhead: "LookAhead",
      obsScanR: "Obs Scan R",
      icpScoreMax: "ICP Maks",
      scanMinX: "Scan Min X",
      scanMaxX: "Scan Max X",
      scanMinY: "Scan Min Y",
      scanMaxY: "Scan Max Y",
      obsThreshold: "Obs Thresh",
      actions: "Aksi",
      undoAction: "Batalkan Aksi",
      saveTerminals: "Simpan Terminal"
    }
  };
  
  const dispatch = createEventDispatcher();

  let editMode = 'edit'; 
  let dragAction = 'none'; 
  
  let selectedIdxs = new Set();
  let undoStack = [];
  
  let customView = null;
  let zoomUndoStack = [];
  
  let rotationCenter = null;
  let rotationInitialPoints = [];
  let dragStartAngle = 0;
  
  let dragStartPos = null;
  let panStartPixel = null;
  let rectStart = null;
  let rectCurrent = null;
  
  let svgElement;
  let dataLayer; 
  let svgWidth = 800;
  let svgHeight = 600;

  $: singleSelectedIdx = selectedIdxs.size === 1 ? Array.from(selectedIdxs)[0] : null;

  const saveState = () => undoStack.push(JSON.parse(JSON.stringify(terminals)));

  function undoLastMove() { 
    if (undoStack.length > 0) {
      terminals = undoStack.pop();
      selectedIdxs = new Set();
    }
  }

  function lockView() { if (!customView) customView = { minX: activeMinX, maxX: activeMaxX, minY: activeMinY, maxY: activeMaxY }; }
  function resetZoom() { customView = zoomUndoStack.length > 0 ? zoomUndoStack.pop() : null; }
  function setMode(mode) { editMode = mode; }

  function getTerminalColor(type) {
    if (type === 1) return 'orange';
    if (type === 2) return 'yellow';
    if (type === 32) return 'green';
    return 'blue';
  }

  function deleteSelectedTerminal() {
    if (selectedIdxs.size === 0) return;
    saveState(); 
    terminals = terminals.filter((_, i) => !selectedIdxs.has(i));
    selectedIdxs = new Set();
  }

  function onKey(event) {
    const key = event.key.toLowerCase();
    if (event.altKey && key === 's') dispatch('save', terminals);
    else if (event.altKey && key === 'z') { editMode === 'zoom' ? resetZoom() : undoLastMove(); } 
    else if (event.altKey && key === 'e') setMode('edit');
    else if (event.altKey && key === 'x') setMode('zoom');
    else if (key === 'delete') deleteSelectedTerminal(); 
  }

  function getGlobalCoords(event) {
    if (!dataLayer) return { x: 0, y: 0 };
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX; pt.y = event.clientY;
    const svgP = pt.matrixTransform(dataLayer.getScreenCTM().inverse());
    return { x: svgP.x, y: svgP.y };
  }

  function onPress(event) {
    const coords = getGlobalCoords(event);
    
    if (event.button === 2) {
      let closestIdx = -1;
      let minDist = Infinity;
      
      terminals.forEach((t, i) => {
        const dist = Math.sqrt(Math.pow(t.x - coords.x, 2) + Math.pow(t.y - coords.y, 2));
        const hitRadius = Math.max(t.radius_area, pointRadius * 4.0);
        if (dist < minDist && dist < hitRadius) { minDist = dist; closestIdx = i; }
      });

      if (closestIdx !== -1 && selectedIdxs.has(closestIdx)) {
        dragAction = 'rotate';
        dragStartPos = coords;
        let cx = 0, cy = 0;
        for (let i of selectedIdxs) { cx += terminals[i].x; cy += terminals[i].y; }
        cx /= selectedIdxs.size; cy /= selectedIdxs.size;
        rotationCenter = { x: cx, y: cy };
        rotationInitialPoints = terminals.map(t => ({...t}));
        dragStartAngle = Math.atan2(coords.y - rotationCenter.y, coords.x - rotationCenter.x);
        saveState();
        lockView();
        return;
      }
      
      dragAction = 'pan';
      panStartPixel = { x: event.clientX, y: event.clientY };
      lockView(); 
      return; 
    }

    dragStartPos = coords;

    if (editMode === 'edit') {
      let closestIdx = -1;
      let minDist = Infinity;
      
      terminals.forEach((t, i) => {
        const dist = Math.sqrt(Math.pow(t.x - coords.x, 2) + Math.pow(t.y - coords.y, 2));
        const hitRadius = Math.max(t.radius_area, pointRadius * 4.0);
        if (dist < minDist && dist < hitRadius) { minDist = dist; closestIdx = i; }
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
    else if (editMode === 'add') {
      saveState();
      const newId = terminals.length > 0 ? Math.max(...terminals.map(t => t.id)) + 1 : 0;
      const newTerminal = {
        type: 1, id: newId, x: coords.x, y: coords.y, theta: 0.0,
        max_vx: 1.0, max_vy: 1.0, max_vtheta: 0.5, radius_area: 1.0,
        lookahead_distance: 1.0, obs_scan_r: 2.0, icp_score_max: 1.0,
        scan_min_x: -0.4, scan_max_x: 3.0, scan_min_y: -1.0, scan_max_y: 1.0, obs_threshold: 50000
      };
      
      terminals = [...terminals, newTerminal];
      selectedIdxs = new Set([terminals.length - 1]);
      setMode('edit'); 
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
    
    const coords = getGlobalCoords(event);
    const dx = coords.x - dragStartPos.x;
    const dy = coords.y - dragStartPos.y;

    if (dragAction === 'rotate' && rotationCenter) {
      const currentAngle = Math.atan2(coords.y - rotationCenter.y, coords.x - rotationCenter.x);
      const angleDiff = currentAngle - dragStartAngle;
      const cosA = Math.cos(angleDiff);
      const sinA = Math.sin(angleDiff);
      
      terminals = rotationInitialPoints.map((t, i) => {
        if (selectedIdxs.has(i)) {
          const dx = t.x - rotationCenter.x;
          const dy = t.y - rotationCenter.y;
          
          let newTheta = (t.theta || 0) + angleDiff;
          while (newTheta > Math.PI) newTheta -= 2 * Math.PI;
          while (newTheta < -Math.PI) newTheta += 2 * Math.PI;
          
          return {
            ...t,
            x: rotationCenter.x + (dx * cosA - dy * sinA),
            y: rotationCenter.y + (dx * sinA + dy * cosA),
            theta: newTheta
          };
        }
        return t;
      });
      return;
    }

    if (dragAction === 'move' && selectedIdxs.size > 0) {
      for (let i of selectedIdxs) { terminals[i].x += dx; terminals[i].y += dy; }
      dragStartPos = coords;
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
        terminals.forEach((t, i) => { if (t.x >= xMin && t.x <= xMax && t.y >= yMin && t.y <= yMax) newSelection.add(i); });
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

  $: allPointsX = [...terminals.map(t => t.x), ...waypoints.map(w => w.x)];
  $: allPointsY = [...terminals.map(t => t.y), ...waypoints.map(w => w.y)];

  $: minPx = allPointsX.length ? Math.min(...allPointsX) : Infinity;
  $: maxPx = allPointsX.length ? Math.max(...allPointsX) : -Infinity;
  $: minPy = allPointsY.length ? Math.min(...allPointsY) : Infinity;
  $: maxPy = allPointsY.length ? Math.max(...allPointsY) : -Infinity;

  $: mapMinX = mapImage ? mapImage.originX : Infinity;
  $: mapMaxX = mapImage ? mapImage.originX + (mapImage.width * mapImage.resolution) : -Infinity;
  $: mapMinY = mapImage ? mapImage.originY : Infinity;
  $: mapMaxY = mapImage ? mapImage.originY + (mapImage.height * mapImage.resolution) : -Infinity;

  $: rawMinX = Math.min(minPx, mapMinX) === Infinity ? 0 : Math.min(minPx, mapMinX);
  $: rawMaxX = Math.max(maxPx, mapMaxX) === -Infinity ? 10 : Math.max(maxPx, mapMaxX);
  $: rawMinY = Math.min(minPy, mapMinY) === Infinity ? 0 : Math.min(minPy, mapMinY);
  $: rawMaxY = Math.max(maxPy, mapMaxY) === -Infinity ? 10 : Math.max(maxPy, mapMaxY);
  
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
  $: lineStroke = 2 * pxScale; 
  $: pointRadius = 3 * pxScale;
  $: fontSize = 16 * pxScale;
  
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
  $: wpPointsString = waypoints.map(w => `${w.x},${w.y}`).join(' ');
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
        <li><strong>{i18n[lang].labelRotate}:</strong> {i18n[lang].rotateDesc}</li>
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
      <h4>{i18n[lang].addingModifying}</h4>
      <ul>
        <li><strong>{i18n[lang].labelAdd}:</strong> {i18n[lang].addDesc}</li>
        <li><strong>{i18n[lang].labelProperties}:</strong> {@html i18n[lang].propDesc}</li>
      </ul>
    </div>
    <div class="info-section">
      <h4>{i18n[lang].types}</h4>
      <ul>
        <li style="color: orange; font-weight: bold;">{i18n[lang].type1}</li>
        <li style="color: #c9aa00; font-weight: bold;">{i18n[lang].type2}</li>
        <li style="color: green; font-weight: bold;">{i18n[lang].type32}</li>
      </ul>
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

        {#if waypoints.length > 0}
  <polyline points={wpPointsString} fill="none" stroke="rgba(0, 100, 255, 0.6)" stroke-width={lineStroke} />
  {#each waypoints as wp}
    <circle cx={wp.x} cy={wp.y} r={pointRadius * 0.8} fill="#0064ff" fill-opacity="0.7" />
  {/each}
{/if}

        {#if rectStart && rectCurrent && dragAction === 'zoomRect'}
          <rect x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)} width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)} fill="rgba(0, 100, 255, 0.15)" stroke="blue" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}" />
        {/if}

        {#each terminals as t, i}
          <circle cx={t.x} cy={t.y} r={t.radius_area || 1.0} fill={selectedIdxs.has(i) ? "red" : getTerminalColor(t.type)} fill-opacity={selectedIdxs.has(i) ? "0.9" : "0.5"} stroke={selectedIdxs.has(i) ? "red" : getTerminalColor(t.type)} stroke-width={lineStroke * 2} class="hoverable-point" />
          <circle cx={t.x} cy={t.y} r={pointRadius * 1.5} fill={selectedIdxs.has(i) ? "red" : getTerminalColor(t.type)} />
          <line x1={t.x} y1={t.y} x2={t.x + (t.radius_area * 0.8) * Math.cos(t.theta)} y2={t.y + (t.radius_area * 0.8) * Math.sin(t.theta)} stroke="black" stroke-width={lineStroke * 1.5} />
          <circle cx={t.x + (t.radius_area * 0.8) * Math.cos(t.theta)} cy={t.y + (t.radius_area * 0.8) * Math.sin(t.theta)} r={pointRadius * 1.2} fill="black" />
          
          <g transform="translate({t.x}, {t.y}) scale(1, -1)">
            <text x="0" y="0" text-anchor="middle" dominant-baseline="central" font-size={fontSize} font-weight="bold" fill="black">{t.id}</text>
          </g>
        {/each}

        {#if rectStart && rectCurrent && dragAction === 'rect'}
          <rect x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)} width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)} fill="rgba(0, 200, 0, 0.1)" stroke="green" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}" />
        {/if}
      </g>

      <g class="grid-system">
        {#each xTicks as x}
          <line x1={x} y1={-activeMaxY} x2={x} y2={-activeMinY} stroke="rgba(200,200,200,0.5)" stroke-width={gridStroke} />
          <text x={x} y={-activeMinY - (fontSize * 0.5)} font-size={fontSize * 0.8} fill="#555" text-anchor="middle" paint-order="stroke" stroke="white" stroke-width={pxScale * 4}>{formatTick(x)}</text>
        {/each}
        {#each yTicks as y}
          <line x1={activeMinX} y1={-y} x2={activeMaxX} y2={-y} stroke="rgba(200,200,200,0.5)" stroke-width={gridStroke} />
          <text x={activeMinX + (fontSize * 0.5)} y={-y + (fontSize * 0.3)} font-size={fontSize * 0.8} fill="#555" text-anchor="start" paint-order="stroke" stroke="white" stroke-width={pxScale * 4}>{formatTick(y)}</text>
        {/each}
      </g>
    </svg>
  </div>

  <!-- RIGHT: TOOLBAR -->
  <div class="toolbar">
    <h3>{i18n[lang].tools}</h3>
    <button class:active={editMode === 'edit'} on:click={() => setMode('edit')}><span>👆</span> {i18n[lang].selectEdit}</button>
    <button class:active={editMode === 'add'} on:click={() => setMode('add')}><span>➕</span> {i18n[lang].addTerminal}</button>
    <button class:active={editMode === 'zoom'} on:click={() => setMode('zoom')}><span>🔍</span> {i18n[lang].zoom}</button>
    
    <div class="spacer"></div>

    <h3>{i18n[lang].modifySelection}</h3>

    <div class="spacer"></div>

    {#if singleSelectedIdx !== null && terminals[singleSelectedIdx]}
      <div class="properties-panel">
        <div class="panel-header"><strong>{i18n[lang].terminalId}: {terminals[singleSelectedIdx].id}</strong></div>
        <div class="properties-grid">
          <label><span>{i18n[lang].typeLabel}</span><input type="number" bind:value={terminals[singleSelectedIdx].type}></label>
          <label><span>{i18n[lang].radiusArea}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].radius_area}></label>
          <label><span>{i18n[lang].thetaRad}</span><input type="number" step="0.05" bind:value={terminals[singleSelectedIdx].theta}></label>
          <label><span>{i18n[lang].lookAhead}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].lookahead_distance}></label>
          <label><span>{i18n[lang].maxVx}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].max_vx}></label>
          <label><span>{i18n[lang].maxVy}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].max_vy}></label>
          <label><span>{i18n[lang].maxVtheta}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].max_vtheta}></label>
          <label><span>{i18n[lang].icpScoreMax}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].icp_score_max}></label>
          <label><span>{i18n[lang].obsScanR}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].obs_scan_r}></label>
          <label><span>{i18n[lang].obsThreshold}</span><input type="number" step="1000" bind:value={terminals[singleSelectedIdx].obs_threshold}></label>
          <label><span>{i18n[lang].scanMinX}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].scan_min_x}></label>
          <label><span>{i18n[lang].scanMaxX}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].scan_max_x}></label>
          <label><span>{i18n[lang].scanMinY}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].scan_min_y}></label>
          <label><span>{i18n[lang].scanMaxY}</span><input type="number" step="0.1" bind:value={terminals[singleSelectedIdx].scan_max_y}></label>
        </div>
      </div>
    {:else if selectedIdxs.size > 1}
      <div class="properties-panel">
        <div class="panel-header"><strong>{selectedIdxs.size} {i18n[lang].terminalsSelected}</strong></div>
        <p style="font-size: 11px; color: #666; margin: 0;">{i18n[lang].selectSinglePrompt}</p>
      </div>
    {/if}

    <button class="delete-btn" on:click={deleteSelectedTerminal} disabled={selectedIdxs.size === 0}><span>🗑️</span> {i18n[lang].deleteSelected}</button>

    <div class="spacer"></div>

    <h3>{i18n[lang].actions}</h3>
    <button class="action-btn" on:click={undoLastMove}><span>↩️</span> {i18n[lang].undoAction}</button>
    <button class="save-btn" on:click={() => dispatch('save', terminals)}><span>💾</span> {i18n[lang].saveTerminals}</button>
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
  .hoverable-point { transition: fill-opacity 0.2s; }
  .hoverable-point:hover { cursor: pointer; fill-opacity: 0.8 !important; }
  svg { width: 100%; height: 100%; cursor: crosshair; user-select: none; display: block; }
  .grid-system text { font-family: sans-serif; font-weight: bold; pointer-events: none; }
  .btn-row { display: flex; gap: 6px; }
  .icon-btn { flex: 1; justify-content: center; padding: 10px 5px; }

  button { display: flex; align-items: center; gap: 8px; padding: 10px; font-size: 14px; text-align: left; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; transition: all 0.2s; color: #333; }
  button:hover:not(:disabled) { background: #f0f0f0; border-color: #bbb; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.active { background: #e0edff; border-color: #0064ff; color: #004dc4; font-weight: bold; }
  
  .delete-btn { background: #ffebee; border-color: #ef9a9a; color: #c62828; margin-top: 5px; }
  .delete-btn:hover:not(:disabled) { background: #ffcdd2; }
  .action-btn { background: #fff3e0; border-color: #ffcc80; }
  .action-btn:hover { background: #ffe0b2; }
  .save-btn { background: #e8f5e9; border-color: #a5d6a7; font-weight: bold; }
  .save-btn:hover { background: #c8e6c9; }

  .properties-panel { background: #fff; border: 1px solid #cce5ff; border-radius: 4px; padding: 10px; display: flex; flex-direction: column; gap: 8px; box-shadow: inset 0 0 5px rgba(0,100,255,0.05); }
  .panel-header { font-size: 14px; color: #004dc4; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
  .properties-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
  .properties-panel label { display: flex; flex-direction: column; font-size: 11px; color: #555; font-weight: bold; gap: 2px; }
  .properties-panel input { padding: 4px; font-family: monospace; border: 1px solid #ccc; border-radius: 3px; font-size: 12px; width: 100%; box-sizing: border-box; }
</style>