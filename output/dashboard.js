/**
 * Slide Comparison Hub Dashboard Script
 */

document.addEventListener('DOMContentLoaded', () => {
  const projects = window.PROJECTS_DATA || [];
  const grid = document.getElementById('projectsGrid');
  const searchInput = document.getElementById('projectSearchInput');
  const countEl = document.getElementById('totalProjectsCount');
  const btnToggleTheme = document.getElementById('btnToggleTheme');

  countEl.textContent = projects.length;

  function renderProjects(items) {
    grid.innerHTML = '';
    if (items.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
          <h3>검색 결과가 없습니다</h3>
          <p style="margin-top: 8px;">다른 키워드로 검색해 보세요.</p>
        </div>
      `;
      return;
    }

    items.forEach(proj => {
      const card = document.createElement('a');
      card.className = 'project-card';
      card.href = proj.url;

      // Base file and target files
      const baseFile = proj.files.find(f => f.is_base) || proj.files[0];
      const targetFiles = proj.files.filter(f => !f.is_base);

      let filesHtml = `
        <div class="card-file-item">
          <span class="file-name"><span class="file-pill pill-base">기준</span> ${escapeHtml(baseFile.name)}</span>
          <span style="color:var(--text-muted);font-size:11px;">${baseFile.slide_count}장</span>
        </div>
      `;

      targetFiles.forEach((tf, idx) => {
        filesHtml += `
          <div class="card-file-item">
            <span class="file-name"><span class="file-pill pill-target">비교 ${idx+1}</span> ${escapeHtml(tf.name)}</span>
            <span style="color:var(--text-muted);font-size:11px;">${tf.slide_count}장</span>
          </div>
        `;
      });

      card.innerHTML = `
        <div class="card-header-bar">
          <span class="card-badge">${proj.files.length}개 파일 비교</span>
          <span class="card-date">${proj.updated_at || '최근 업데이트'}</span>
        </div>
        <div class="card-content">
          <h3 class="card-title">${escapeHtml(proj.title)}</h3>
          <p class="card-desc">기준 슬라이드 ${baseFile.slide_count}장 대비 ${targetFiles.length}개 비교본 매핑 완료</p>
          <div class="card-files-list">
            ${filesHtml}
          </div>
          <div class="card-footer">
            <span class="card-stats">총 <strong>${proj.files.reduce((sum, f) => sum + (f.slide_count || 0), 0)}</strong>장</span>
            <span class="btn-open-viewer">
              비교 뷰어 열기
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            </span>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  // Search filter
  searchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    if (!q) {
      renderProjects(projects);
      return;
    }
    const filtered = projects.filter(p => {
      const matchTitle = p.title.toLowerCase().includes(q);
      const matchFiles = p.files.some(f => f.name.toLowerCase().includes(q));
      return matchTitle || matchFiles;
    });
    renderProjects(filtered);
  });

  // Dark mode
  btnToggleTheme.addEventListener('click', () => {
    document.body.classList.toggle('theme-dark');
    document.body.classList.toggle('theme-light');
  });

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  renderProjects(projects);
});
