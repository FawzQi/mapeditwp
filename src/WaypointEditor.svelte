<script>
  import { createEventDispatcher } from 'svelte';
  
  export let waypoints = []; 
  export let mapImage = null;
  
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
    wpOriginX, wpOriginY, wpOriginYaw
  });

  function undoLastMove() { 
    if (undoStack.length > 0) {
      const state = undoStack.pop();
      waypoints = state.waypoints;
      wpOriginX = state.wpOriginX;
      wpOriginY = state.wpOriginY;
      wpOriginYaw = state.wpOriginYaw;
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

  // NEW: Rotate selected waypoints around their own geometric center
  function rotateSelected(angleDegrees) {
    if (selectedIdxs.size === 0) return;
    saveState();
    
    const angleRad = angleDegrees * (Math.PI / 180);
    const cosA = Math.cos(angleRad);
    const sinA = Math.sin(angleRad);
    
    // Find the center point of the current selection
    let cx = 0, cy = 0;
    for (let i of selectedIdxs) {
      cx += waypoints[i].x;
      cy += waypoints[i].y;
    }
    cx /= selectedIdxs.size;
    cy /= selectedIdxs.size;
    
    // Rotate each point around that center
    waypoints = waypoints.map((wp, i) => {
      if (selectedIdxs.has(i)) {
        const dx = wp.x - cx;
        const dy = wp.y - cy;
        return {
          ...wp,
          x: cx + (dx * cosA - dy * sinA),
          y: cy + (dx * sinA + dy * cosA)
        };
      }
      return wp;
    });
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
      
      waypoints.forEach((wp, i) => {
        const dist = Math.sqrt(Math.pow(wp.x - coords.x, 2) + Math.pow(wp.y - coords.y, 2));
        // EDITED: Increased hitbox multiplier from 2.0 to 4.0 to make clicking easier
        if (dist < minDist && dist < (pointRadius * 4.0)) { minDist = dist; closestIdx = i; }
      });

      if (closestIdx !== -1) {
        // NEW: Alt+Click toggle logic for multi-select
        if (event.altKey) {
          if (selectedIdxs.has(closestIdx)) {
            selectedIdxs.delete(closestIdx);
          } else {
            selectedIdxs.add(closestIdx);
          }
          selectedIdxs = selectedIdxs; // Trigger Svelte reactivity
        } else if (!selectedIdxs.has(closestIdx)) {
          selectedIdxs = new Set([closestIdx]); // Normal click (clears other selections)
        }
        
        dragAction = 'move';
        saveState(); 
        lockView();
      } else {
        selectedIdxs = new Set(); 
        dragAction = 'rect';
        rectStart = coords;
        rectCurrent = coords;
      }
    } 
    else if (editMode === 'zoom') {
      dragAction = 'zoomRect';
      rectStart = coords; 
      rectCurrent = coords;
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
      dragStartPos = coords;
      waypoints = waypoints; 
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
    
    dragAction = 'none'; 
    dragStartPos = null; 
  }
  
  $: transformedWaypoints = waypoints.map(w => {
    const cosT = Math.cos(wpOriginYaw);
    const sinT = Math.sin(wpOriginYaw);
    return { x: w.x * cosT - w.y * sinT + wpOriginX, y: w.x * sinT + w.y * cosT + wpOriginY };
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
      <strong>Alt+Z:</strong> Undo • 
      <strong>Alt+Click:</strong> Multi-select •
      <strong>Del:</strong> Delete • 
      <strong>Double-Click:</strong> Auto-fit
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
        
        {#if mapImage}
          <g transform="rotate({(mapImage.originYaw) * 180 / Math.PI}) translate({mapImage.originX}, {mapImage.originY}) translate(0, {mapImage.height * mapImage.resolution}) scale(1, -1)">
            <image x="0" y="0" width={mapImage.width * mapImage.resolution} height={mapImage.height * mapImage.resolution} href={mapImage.url} preserveAspectRatio="none" />
          </g>
        {/if}

        <!-- ZOOM BOX -->
        {#if rectStart && rectCurrent && dragAction === 'zoomRect'}
          <rect 
            x={Math.min(rectStart.x, rectCurrent.x)} y={Math.min(rectStart.y, rectCurrent.y)}
            width={Math.abs(rectCurrent.x - rectStart.x)} height={Math.abs(rectCurrent.y - rectStart.y)}
            fill="rgba(0, 100, 255, 0.15)" stroke="blue" stroke-width={lineStroke} stroke-dasharray="{lineStroke * 2}, {lineStroke * 2}"
          />
        {/if}

        <!-- WAYPOINTS LOCAL LAYER -->
        <g bind:this={wpLayer} transform="translate({0+wpOriginX}, {0+wpOriginY}) rotate({(0+wpOriginYaw) * 180 / Math.PI})">
          
          <polyline points={pointsString} fill="none" stroke="rgba(0, 0, 255, 0.4)" stroke-width={lineStroke} />
          
          {#each waypoints as wp, i}
            <circle cx={wp.x} cy={wp.y} r={(pointRadius>0.05 ? pointRadius : 0.05)} fill={selectedIdxs.has(i) ? "red" : "#0064ff"} />
          {/each}

          <!-- GROUP SELECTION BOX -->
          {#if rectStart && rectCurrent && dragAction === 'rect'}
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
    <button class:active={editMode === 'edit'} on:click={() => setMode('edit')}><span>👆</span> Edit (Alt+E)</button>
    <button class:active={editMode === 'zoom'} on:click={() => setMode('zoom')}><span>🔍</span> Zoom (Alt+X)</button>
    
    <div class="spacer"></div>

    <!-- NEW: Rotate and Modify Section -->
    <h3>Modify Selection</h3>
    <div class="btn-row">
      <button class="icon-btn" on:click={() => rotateSelected(2)} disabled={selectedIdxs.size === 0} title="Rotate   Clockwise">
        <span>rotate ↺</span> 
      </button>
      <button class="icon-btn" on:click={() => rotateSelected(-2)} disabled={selectedIdxs.size === 0} title="Rotate  Counter-Clockwise">
        <span>↻ rotate</span>  
      </button>
    </div>
    
    <button class="delete-btn" on:click={deleteSelectedPoints} disabled={selectedIdxs.size === 0}>
      <span>🗑️</span> Delete (Del)
    </button>

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
  
  .toolbar { width: 210px; display: flex; flex-direction: column; gap: 8px; background: #f9f9f9; padding: 15px; border-radius: 6px; border: 1px solid #ccc; overflow-y: auto; }
  .toolbar h3 { margin: 0 0 2px 0; font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .spacer { flex-grow: 1; min-height: 10px; }
  
  /* Flexbox configuration for the new row of rotation buttons */
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
</style>