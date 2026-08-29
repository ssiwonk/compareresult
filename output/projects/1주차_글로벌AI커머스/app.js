/**
 * Slide Comparison Viewer Application Script
 */

document.addEventListener('DOMContentLoaded', () => {
  if (!window.SLIDE_DATA) {
    console.error('Slide comparison data not loaded!');
    return;
  }

  const data = window.SLIDE_DATA;
  const files = data.files || [];
  const rows = data.rows || [];

  // State
  const state = {
    visibleColumns: files.map((_, i) => true),
    searchQuery: '',
    currentZoom: 1,
    panX: 0,
    panY: 0,
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    activeModalSlide: null, // { fileIndex, slideIndex, slideObj, title }
    flatSlides: [] // for modal prev/next
  };

  // Collect all slides flat list for lightbox navigation
  files.forEach((f, fIdx) => {
    // Collect from rows
    rows.forEach(r => {
      if (fIdx === 0 && r.base_slide) {
        state.flatSlides.push({
          fileIndex: 1,
          fileName: f.name,
          slide: r.base_slide,
          rowIdx: r.row_index
        });
      } else if (fIdx > 0) {
        const target = r.targets[fIdx - 1];
        if (target && target.slides) {
          target.slides.forEach(s => {
            state.flatSlides.push({
              fileIndex: fIdx + 1,
              fileName: f.name,
              slide: s,
              rowIdx: r.row_index
            });
          });
        }
      }
    });
  });

  // DOM Elements
  const appSidebar = document.getElementById('appSidebar');
  const btnToggleSidebar = document.getElementById('btnToggleSidebar');
  const sidebarList = document.getElementById('sidebarList');
  const sidebarSlideCount = document.getElementById('sidebarSlideCount');
  const columnToggles = document.getElementById('columnToggles');
  const comparisonHeaderRow = document.getElementById('comparisonHeaderRow');
  const comparisonGrid = document.getElementById('comparisonGrid');
  const searchInput = document.getElementById('searchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');
  const btnToggleTheme = document.getElementById('btnToggleTheme');
  const mainContent = document.getElementById('mainContent');

  // Modal Elements
  const modal = document.getElementById('lightboxModal');
  const modalImage = document.getElementById('modalImage');
  const modalBadge = document.getElementById('modalBadge');
  const modalTitle = document.getElementById('modalTitle');
  const modalCounter = document.getElementById('modalCounter');
  const btnCloseModal = document.getElementById('btnCloseModal');
  const btnPrevSlide = document.getElementById('btnPrevSlide');
  const btnNextSlide = document.getElementById('btnNextSlide');
  const btnZoomIn = document.getElementById('btnZoomIn');
  const btnZoomOut = document.getElementById('btnZoomOut');
  const btnResetZoom = document.getElementById('btnResetZoom');
  const zoomLevelText = document.getElementById('zoomLevelText');
  const modalBody = document.getElementById('modalBody');

  // 1. Initialize Column Toggles & CSS Var
  function initHeaderControls() {
    columnToggles.innerHTML = '';
    const badgeColors = ['#2563eb', '#059669', '#7c3aed', '#d97706'];

    files.forEach((file, idx) => {
      const btn = document.createElement('button');
      btn.className = 'col-toggle-btn active';
      const color = badgeColors[idx % badgeColors.length];
      btn.innerHTML = `
        <span class="badge-dot" style="background-color: ${color};"></span>
        <span>${idx + 1}. ${escapeHtml(file.name)}</span>
      `;
      btn.addEventListener('click', () => {
        state.visibleColumns[idx] = !state.visibleColumns[idx];
        btn.classList.toggle('active', state.visibleColumns[idx]);
        updateColumnVisibility();
      });
      columnToggles.appendChild(btn);
    });

    sidebarSlideCount.textContent = `${rows.length} 슬라이드`;

    if (data.project_title) {
      document.title = `${data.project_title} - 슬라이드 비교 뷰어`;
      const titleHeader = document.getElementById('projectTitleHeader');
      if (titleHeader) titleHeader.textContent = data.project_title;
    }
  }

  function updateColumnVisibility() {
    const visibleCount = state.visibleColumns.filter(Boolean).length;
    document.documentElement.style.setProperty('--col-count', Math.max(1, visibleCount));

    // Update Header Row columns
    const headerCells = comparisonHeaderRow.querySelectorAll('.col-header-cell');
    headerCells.forEach((cell, idx) => {
      cell.style.display = state.visibleColumns[idx] ? 'flex' : 'none';
    });

    // Update Grid Row columns
    const gridRows = comparisonGrid.querySelectorAll('.comparison-row');
    gridRows.forEach(row => {
      const cells = row.querySelectorAll('.row-col-cell');
      cells.forEach((cell, idx) => {
        cell.style.display = state.visibleColumns[idx] ? 'flex' : 'none';
      });
    });
  }

  // 2. Render Sticky Headers
  function renderHeaderRow() {
    comparisonHeaderRow.innerHTML = '';
    const badgeClasses = ['badge-f1', 'badge-f2', 'badge-f3', 'badge-f4'];

    files.forEach((file, idx) => {
      const cell = document.createElement('div');
      cell.className = 'col-header-cell';
      const badgeCls = badgeClasses[idx % badgeClasses.length];
      const isBaseText = file.is_base ? ' (기준)' : '';
      
      cell.innerHTML = `
        <div class="col-header-title">
          <span class="col-header-badge ${badgeCls}">FILE ${idx + 1}${isBaseText}</span>
          <span class="col-header-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span>
        </div>
        <span class="col-header-count">${file.slide_count}장</span>
      `;
      comparisonHeaderRow.appendChild(cell);
    });
  }

  // 3. Render Sidebar TOC
  function renderSidebar() {
    sidebarList.innerHTML = '';
    rows.forEach((row, rIdx) => {
      const bSlide = row.base_slide;
      const item = document.createElement('a');
      item.className = 'sidebar-item';
      item.href = `#row-${row.row_index}`;
      item.dataset.rowIndex = row.row_index;

      // Match tags for File 2, File 3
      let matchBadgesHtml = '';
      row.targets.forEach((t, tIdx) => {
        const count = t.slides ? t.slides.length : 0;
        const tagClass = `f${tIdx + 2}`;
        const label = count > 0 ? `F${tIdx+2}:${count}` : `F${tIdx+2}:-`;
        matchBadgesHtml += `<span class="match-tag ${tagClass}">${label}</span>`;
      });

      item.innerHTML = `
        <div class="sidebar-item-left">
          <span class="sidebar-num">#${row.row_index}</span>
          <span class="sidebar-title" title="${escapeHtml(bSlide.title)}">${escapeHtml(bSlide.title || '슬라이드 ' + row.row_index)}</span>
        </div>
        <div class="sidebar-match-tags">
          ${matchBadgesHtml}
        </div>
      `;

      item.addEventListener('click', (e) => {
        e.preventDefault();
        const targetRow = document.getElementById(`row-${row.row_index}`);
        if (targetRow) {
          targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
          highlightRow(targetRow);
        }
      });

      sidebarList.appendChild(item);
    });
  }

  function highlightRow(rowEl) {
    rowEl.style.backgroundColor = 'rgba(37, 99, 235, 0.08)';
    setTimeout(() => {
      rowEl.style.backgroundColor = '';
    }, 1500);
  }

  // 4. Render Main Comparison Grid
  function renderComparisonGrid() {
    comparisonGrid.innerHTML = '';

    rows.forEach((row) => {
      const rowDiv = document.createElement('div');
      rowDiv.className = 'comparison-row';
      rowDiv.id = `row-${row.row_index}`;
      rowDiv.dataset.rowIndex = row.row_index;

      // Col 1: Base Slide
      const col1 = document.createElement('div');
      col1.className = 'row-col-cell col-1';
      col1.appendChild(createSlideCard(row.base_slide, 1, files[0].name, row.row_index));
      rowDiv.appendChild(col1);

      // Col 2..N: Target Slides
      row.targets.forEach((target, tIdx) => {
        const fileIdx = tIdx + 2;
        const colN = document.createElement('div');
        colN.className = `row-col-cell col-${fileIdx}`;

        if (!target.slides || target.slides.length === 0) {
          // Empty state
          const empty = document.createElement('div');
          empty.className = 'empty-slide-placeholder';
          empty.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <span>해당 슬라이드 없음</span>
          `;
          colN.appendChild(empty);
        } else {
          const groupDiv = document.createElement('div');
          const count = Math.min(target.slides.length, 4);
          groupDiv.className = `slide-card-group count-${count}`;

          target.slides.forEach(slide => {
            groupDiv.appendChild(createSlideCard(slide, fileIdx, target.file_name, row.row_index));
          });
          colN.appendChild(groupDiv);
        }

        rowDiv.appendChild(colN);
      });

      comparisonGrid.appendChild(rowDiv);
    });
  }

  function createSlideCard(slide, fileIndex, fileName, rowIndex) {
    const card = document.createElement('div');
    card.className = 'slide-card';

    const badgeClasses = ['badge-f1', 'badge-f2', 'badge-f3', 'badge-f4'];
    const badgeCls = badgeClasses[(fileIndex - 1) % badgeClasses.length];

    card.innerHTML = `
      <div class="slide-card-header">
        <span class="slide-card-badge ${badgeCls}">F${fileIndex} · S${slide.num}</span>
        <span class="slide-card-title" title="${escapeHtml(slide.title)}">${escapeHtml(slide.title)}</span>
      </div>
      <div class="slide-img-wrapper">
        <img src="${slide.image}" alt="Slide ${slide.num}" loading="lazy">
        <div class="zoom-overlay-hint">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
          <span>클릭하여 확대</span>
        </div>
      </div>
    `;

    // Click on image opens lightbox modal
    const imgWrapper = card.querySelector('.slide-img-wrapper');
    imgWrapper.addEventListener('click', () => {
      openLightbox({
        fileIndex,
        fileName,
        slide,
        rowIndex
      });
    });

    return card;
  }

  // 5. Lightbox Modal Logic
  function openLightbox(slideInfo) {
    state.activeModalSlide = slideInfo;
    state.currentZoom = 1;
    state.panX = 0;
    state.panY = 0;
    applyTransform();

    modalImage.src = slideInfo.slide.image;
    modalBadge.textContent = `FILE ${slideInfo.fileIndex} (슬라이드 ${slideInfo.slide.num})`;
    modalBadge.className = `modal-badge badge-f${slideInfo.fileIndex}`;
    modalTitle.textContent = slideInfo.slide.title || slideInfo.fileName;

    // Find index in flatSlides
    const currentIndex = state.flatSlides.findIndex(
      item => item.fileIndex === slideInfo.fileIndex && item.slide.num === slideInfo.slide.num
    );
    if (currentIndex >= 0) {
      modalCounter.textContent = `${currentIndex + 1} / ${state.flatSlides.length}`;
    }

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  function applyTransform() {
    modalImage.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.currentZoom})`;
    zoomLevelText.textContent = `${Math.round(state.currentZoom * 100)}%`;
  }

  function setZoom(newZoom) {
    state.currentZoom = Math.max(0.5, Math.min(4.0, newZoom));
    if (state.currentZoom === 1) {
      state.panX = 0;
      state.panY = 0;
    }
    applyTransform();
  }

  function navigateModal(direction) {
    if (!state.activeModalSlide) return;
    const currentIndex = state.flatSlides.findIndex(
      item => item.fileIndex === state.activeModalSlide.fileIndex && item.slide.num === state.activeModalSlide.slide.num
    );
    if (currentIndex < 0) return;

    let targetIndex = currentIndex + direction;
    if (targetIndex < 0) targetIndex = state.flatSlides.length - 1;
    if (targetIndex >= state.flatSlides.length) targetIndex = 0;

    const nextItem = state.flatSlides[targetIndex];
    openLightbox({
      fileIndex: nextItem.fileIndex,
      fileName: nextItem.fileName,
      slide: nextItem.slide,
      rowIndex: nextItem.rowIdx
    });
  }

  // Lightbox Event Listeners
  btnCloseModal.addEventListener('click', closeLightbox);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeLightbox();
  });

  btnPrevSlide.addEventListener('click', () => navigateModal(-1));
  btnNextSlide.addEventListener('click', () => navigateModal(1));

  btnZoomIn.addEventListener('click', () => setZoom(state.currentZoom + 0.25));
  btnZoomOut.addEventListener('click', () => setZoom(state.currentZoom - 0.25));
  btnResetZoom.addEventListener('click', () => setZoom(1));

  modalBody.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    setZoom(state.currentZoom + delta);
  });

  // Drag to pan
  modalBody.addEventListener('mousedown', (e) => {
    if (state.currentZoom > 1) {
      state.isDragging = true;
      state.dragStartX = e.clientX - state.panX;
      state.dragStartY = e.clientY - state.panY;
    }
  });

  window.addEventListener('mousemove', (e) => {
    if (state.isDragging) {
      state.panX = e.clientX - state.dragStartX;
      state.panY = e.clientY - state.dragStartY;
      applyTransform();
    }
  });

  window.addEventListener('mouseup', () => {
    state.isDragging = false;
  });

  // 6. Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (modal.style.display === 'flex') {
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') navigateModal(-1);
      if (e.key === 'ArrowRight') navigateModal(1);
    }
  });

  // 7. Search Filter
  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    state.searchQuery = q;
    btnClearSearch.style.display = q ? 'block' : 'none';

    rows.forEach(row => {
      const rowEl = document.getElementById(`row-${row.row_index}`);
      const sidebarEl = sidebarList.querySelector(`[data-row-index="${row.row_index}"]`);
      if (!rowEl) return;

      if (!q) {
        rowEl.style.display = 'grid';
        if (sidebarEl) sidebarEl.style.display = 'flex';
        return;
      }

      // Check match in base slide or target slides text
      let match = (row.base_slide.text || '').toLowerCase().includes(q) ||
                  (row.base_slide.title || '').toLowerCase().includes(q);

      if (!match) {
        row.targets.forEach(t => {
          if (t.slides) {
            t.slides.forEach(s => {
              if ((s.text || '').toLowerCase().includes(q) || (s.title || '').toLowerCase().includes(q)) {
                match = true;
              }
            });
          }
        });
      }

      rowEl.style.display = match ? 'grid' : 'none';
      if (sidebarEl) sidebarEl.style.display = match ? 'flex' : 'none';
    });
  });

  btnClearSearch.addEventListener('click', () => {
    searchInput.value = '';
    searchInput.dispatchEvent(new Event('input'));
  });

  // 8. Sidebar Toggle & Density & Theme
  btnToggleSidebar.addEventListener('click', () => {
    appSidebar.classList.toggle('collapsed');
  });

  btnToggleTheme.addEventListener('click', () => {
    document.body.classList.toggle('theme-dark');
    document.body.classList.toggle('theme-light');
  });

  // Utility: Escape HTML
  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Initial Boot
  initHeaderControls();
  renderHeaderRow();
  renderSidebar();
  renderComparisonGrid();
  updateColumnVisibility();
});
