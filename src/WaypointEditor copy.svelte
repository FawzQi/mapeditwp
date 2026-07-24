<script>
  import { createEventDispatcher } from 'svelte';
  
  export let waypoints = []; 
  export let mapImage = null;
  
  const dispatch = createEventDispatcher();

  let editMode = 'normal';
  let selectedIdxs = new Set();
  let selectedIdxSingle = null;
  let undoStack = [];
  
  let customView = null;
  let zoomUndoStack = [];
  
  // NEW: Waypoint Transform State
  let wpOriginX = 0;
  let wpOriginY = 0;
  let wpOriginYaw = 0; // in radians
  
  let isDragging = false;
  let dragStartPos = null;
  let isPanning = false;
  let panStartPixel = null;
  let rectStart = null;
  let rectCurrent = null;
  
  let svgElement;
  let dataLayer; // Global layer (handles SVG aspect inversion)
  let wpLayer;   // Local layer (handles Waypoint Origin transformations)
  let svgWidth = 800;
  let svgHeight = 600;

  // Save the full state including origins to the undo stack
  const saveState = () => undoStack.push({
    waypoints: JSON.parse(JSON.stringify(waypoints)),
    wpOriginX, wpOriginY, wpOriginYaw
  });

  function undoLastMove() { 
    if (undoStack.length > 0) {
      const state = undoStack.pop();
      waypoints = state.waypoints;
      wpOriginX = state.wpOriginX;
      wpOriginY = state.wpOriginY;
      wpOriginYaw = state.wpOriginYaw;
    }
  }

  function lockView() { if (!customView) customView = { minX: activeMinX, maxX: activeMaxX, minY: activeMinY, maxY: activeMaxY }; }
  function resetZoom() { customView = zoomUndoStack.length > 0 ? zoomUndoStack.pop() : null; }
  function setMode(mode) { editMode = mode; }

  // Permanently bakes the visual origin shift into the CSV points data
  function bakeTransform() {
    saveState();
    waypoints = waypoints.map(w => {
      const cosT = Math.cos(wpOriginYaw);
      const sinT = Math.sin(wpOriginYaw);
      return {
        ...w, // Preserves extra CSV columns like fb_velocity and fb_steering
        x: w.x * cosT - w.y * sinT + wpOriginX,
        y: w.x * sinT + w.y * cosT + wpOriginY
      };
    });
    wpOriginX = 0;
    wpOriginY = 0;
    wpOriginYaw = 0;
  }

  function onKey(event) {
    const key = event.key.toLowerCase();
    if (event.altKey && key === 's') dispatch('save', waypoints);
    else if (event.altKey && key === 'z') { editMode === 'zoom' ? resetZoom() : undoLastMove(); } 
    else if (event.altKey && key === 'g') setMode('group');
    else if (event.altKey && key === 'm') setMode('move');
    else if (event.altKey && key === 'n') setMode('normal');
    else if (event.altKey && key === 'x') setMode('zoom');
  }

  // --- MOUSE COORDINATE HELPERS ---
  // Returns coordinates in the global map frame (used for Panning and Zoom Box)
  function getGlobalCoords(event) {
    if (!dataLayer) return { x: 0, y: 0 };
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX; pt.y = event.clientY;
    const svgP = pt.matrixTransform(dataLayer.getScreenCTM().inverse());
    return { x: svgP.x, y: svgP.y };
  }

  // Returns coordinates relative to the shifted/rotated Waypoint frame (used for dragging & selecting points)
  function getLocalCoords(event) {
    if (!wpLayer) return { x: 0, y: 0 };
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX; pt.y = event.clientY;
    const svgP = pt.matrixTransform(wpLayer.getScreenCTM().inverse());
    return { x: svgP.x, y: svgP.y };
  }

  function onPress(event) {
    if (event.button === 2) {
      isPanning = true;
      panStartPixel = { x: event.clientX, y: event.clientY };
      lockView(); 
      return; 
    }

    // Determine context: Zoom works on global map, all others work on the local waypoint frame
    const coords = (editMode === 'zoom') ? getGlobalCoords(event) : getLocalCoords(event);
    dragStartPos = coords;
    isDragging = true;

    if (editMode === 'normal') {
      let closestIdx = -1;
      let minDist = Infinity;
      waypoints.forEach((wp, i) => {
        const dist = Math.sqrt(Math.pow(wp.x - coords.x, 2) + Math.pow(wp.y - coords.y, 2));
        if (dist < minDist && dist < (pointRadius * 1.5)) { minDist = dist; closestIdx = i; }
      });
      if (closestIdx !== -1) { selectedIdxSingle = closestIdx; saveState(); lockView(); }
    } 
    else if (editMode === 'move' && selectedIdxs.size > 0) { saveState(); lockView(); } 
    else if (editMode === 'group' || editMode === 'zoom') { rectStart = coords; rectCurrent = coords; }
  }

  function onMotion(event) {
    if (isPanning && panStartPixel) {
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

    if (!isDragging || !dragStartPos) return;
    
    const coords = (editMode === 'zoom') ? getGlobalCoords(event) : getLocalCoords(event);
    const dx = coords.x - dragStartPos.x;
    const dy = coords.y - dragStartPos.y;

    if (editMode === 'normal' && selectedIdxSingle !== null) {
      waypoints[selectedIdxSingle].x += dx; waypoints[selectedIdxSingle].y += dy; dragStartPos = coords;
    } else if (editMode === 'move' && selectedIdxs.size > 0) {
      for (let i of selectedIdxs) { waypoints[i].x += dx; waypoints[i].y += dy; }
      dragStartPos = coords;
    } else if (editMode === 'group' || editMode === 'zoom') {
      rectCurrent = coords;
    }
  }

  function onRelease() {
    if (isPanning) { isPanning = false; panStartPixel = null; }
    if ((editMode === 'group' || editMode === 'zoom') && rectStart && rectCurrent) {
      const xMin = Math.min(rectStart.x, rectCurrent.x); const xMax = Math.max(rectStart.x, rectCurrent.x);
      const yMin = Math.min(rectStart.y, rectCurrent.y); const yMax = Math.max(rectStart.y, rectCurrent.y);

      if (editMode === 'group') {
        selectedIdxs = new Set();
        waypoints.forEach((wp, i) => { if (wp.x >= xMin && wp.x <= xMax && wp.y >= yMin && wp.y <= yMax) selectedIdxs.add(i); });
      } else if (editMode === 'zoom') {
        if (xMax - xMin > activeRangeX * 0.02 && yMax - yMin > activeRangeY * 0.02) {
          zoomUndoStack.push(customView ? { ...customView } : null);
          customView = { minX: xMin, maxX: xMax, minY: yMin, maxY: yMax };
        }
        editMode = 'normal'; 
      }
      rectStart = null; rectCurrent = null;
    }
    isDragging = false; dragStartPos = null; selectedIdxSingle = null; selectedIdxs = selectedIdxs; 
  }
  
  // Calculate transformed bounds so Auto-Fit centers on the visually shifted waypoints
  $: transformedWaypoints = waypoints.map(w => {
    const cosT = Math.cos(wpOriginYaw);
    const sinT = Math.sin(wpOriginYaw);
    return {
        x: w.x * cosT - w.y * sinT + wpOriginX,
        y: w.x * sinT + w.y * cosT + wpOriginY
    };
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
  <div class="map-container">
    <div class="hints-overlay">
      <strong>Alt+Z:</strong> {editMode === 'zoom' ? 'Undo Zoom' : 'Undo Edit'} • 
      <strong>Double-Click:</strong> Auto-fit • 
      <strong>Right-Click & Drag:</strong> Pan
    </div>

    <svg 
      bind:this={svgElement} bind:clientWidth={svgWidth} bind:clientHeight={svgHeight}
      viewBox="{activeMinX} {-activeMaxY} {activeRangeX} {activeRangeY}"
      preserveAspectRatio="none"
      on:mousedown={onPress} on:mousemove={onMotion} on:mouseup={onRelease} on:mouseleave={onRelease}
      on:dblclick={resetZoom} on:contextmenu|preventDefault 
    >
      
      <!-- GLOBAL LAYER -->
      <g bind:this={dataLayer} transform="scale(1, -1)">
        
        <!-- BACKGROUND MAP IMAGE[cite: 6] -->
        {#if mapImage}
          <g transform="translate({mapImage.originX}, {mapImage.originY}) rotate({(mapImage.originYaw) * 180 / Math.PI}) translate(0, {mapImage.height * mapImage.resolution}) scale(1, -1)">
            <image x="0" y="0" width={mapImage.width * mapImage.resolution} height={mapImage.height * mapImage.resolution} href={mapImage.url} preserveAspectRatio="none" />
          </g>
        {/if}

        <!-- ZOOM BOX (Drawn in global space so it ignores waypoint rotations) -->
        {#if rectStart && rectCurrent && editMode === 'zoom'}
          <rect 
            x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)}
            width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)}
            fill="rgba(0, 100, 255, 0.15)" stroke="blue" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}"
          />
        {/if}

        <!-- WAYPOINTS LOCAL LAYER -->
        <g bind:this={wpLayer} transform="translate({0+wpOriginX}, {0+wpOriginY}) rotate({(0+wpOriginYaw) * 180 / Math.PI})">
          
          <polyline points={pointsString} fill="none" stroke="blue" stroke-width={lineStroke} />
          
          {#each waypoints as wp, i}
            <circle cx={wp.x} cy={wp.y} r={(pointRadius>0.05 ? pointRadius : 0.05)} fill={selectedIdxs.has(i) ? "red" : "#0064ff"} />
          {/each}

          <!-- GROUP SELECTION BOX (Drawn in local space so it follows the trajectory's rotation) -->
          {#if rectStart && rectCurrent && editMode === 'group'}
            <rect 
              x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)}
              width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)}
              fill="rgba(0, 200, 0, 0.1)" stroke="green" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}"
            />
          {/if}

        </g>
      </g>

      <!-- GRID SYSTEM -->
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

  <div class="toolbar">
    <h3>Tools</h3>
    <button class:active={editMode === 'normal'} on:click={() => setMode('normal')}><span>⚪</span> Normal (Alt+N)</button>
    <button class:active={editMode === 'group'} on:click={() => setMode('group')}><span>🟡</span> Group (Alt+G)</button>
    <button class:active={editMode === 'move'} on:click={() => setMode('move')}><span>🟣</span> Move (Alt+M)</button>
    <button class:active={editMode === 'zoom'} on:click={() => setMode('zoom')}><span>🔍</span> Zoom (Alt+X)</button>
    
    <div class="spacer"></div>

    <h3>WP Origin</h3>
    <div class="origin-inputs">
      <label>X: <input type="number" step="0.5" bind:value={wpOriginX}></label>
      <label>Y: <input type="number" step="0.5" bind:value={wpOriginY}></label>
      <label>Yaw (rad): <input type="number" step="0.05" bind:value={wpOriginYaw}></label>
      <button class="bake-btn" on:click={bakeTransform}>Apply to Points</button>
    </div>

    <div class="spacer"></div>

    <h3>Actions</h3>
    <button class="action-btn" on:click={undoLastMove}><span>↩️</span> Undo (Alt+Z)</button>
    <button class="save-btn" on:click={() => dispatch('save', waypoints)}><span>💾</span> Save Map (Alt+S)</button>
  </div>
</div>

<style>
  .editor-layout { display: flex; gap: 15px; height: 85vh; width: 100%; font-family: sans-serif; }
  .map-container { flex: 1; position: relative; border: 1px solid #ccc; border-radius: 6px; overflow: hidden; background: #ffffff; }
    
  .map-container {
    background-image: linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%);
    background-size: 20px 20px;
    background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
  }
  
  .hints-overlay { position: absolute; top: 10px; right: 15px; background: rgba(255, 255, 255, 0.9); padding: 6px 12px; border-radius: 4px; font-size: 12px; color: #444; box-shadow: 0 1px 4px rgba(0,0,0,0.1); pointer-events: none; z-index: 10; }
  svg { width: 100%; height: 100%; cursor: crosshair; user-select: none; display: block; }
  .grid-system text { font-family: sans-serif; font-weight: bold; pointer-events: none; }
  
  .toolbar { width: 200px; display: flex; flex-direction: column; gap: 8px; background: #f9f9f9; padding: 15px; border-radius: 6px; border: 1px solid #ccc; overflow-y: auto; }
  .toolbar h3 { margin: 0 0 2px 0; font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .spacer { flex-grow: 1; min-height: 10px; }
  
  button { display: flex; align-items: center; gap: 8px; padding: 10px; font-size: 14px; text-align: left; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; transition: all 0.2s; color: #333; }
  button:hover { background: #f0f0f0; border-color: #bbb; }
  button.active { background: #e0edff; border-color: #0064ff; color: #004dc4; font-weight: bold; }
  .action-btn { background: #fff3e0; border-color: #ffcc80; }
  .action-btn:hover { background: #ffe0b2; }
  .save-btn { background: #e8f5e9; border-color: #a5d6a7; font-weight: bold; }
  .save-btn:hover { background: #c8e6c9; }

  /* Origin Input Styling */
  .origin-inputs {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: #fff;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 13px;
  }
  .origin-inputs label {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 600;
    color: #444;
  }
  .origin-inputs input {
    width: 75px;
    padding: 4px;
    font-family: monospace;
    border: 1px solid #ccc;
    border-radius: 3px;
  }
  .bake-btn {
    margin-top: 4px;
    justify-content: center;
    background: #e3f2fd;
    border-color: #90caf9;
    color: #1565c0;
    font-weight: bold;
    padding: 6px;
  }
  .bake-btn:hover { background: #bbdefb; }
</style>