
        // ======================================================
        // INITIALIZATION
        // ======================================================
        document.addEventListener('DOMContentLoaded', () => {
            // ======================================================
            // THEME SWITCHER
            // ======================================================
            const themeToggle = document.getElementById('theme-toggle');
            const htmlEl = document.documentElement;

            themeToggle.addEventListener('click', () => {
                const isDark = htmlEl.classList.toggle('dark');
                htmlEl.classList.toggle('light', !isDark);
                themeToggle.textContent = isDark ? 'LIGHT' : 'DARK';
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
            });
            // Set theme from local storage
            const storedTheme = localStorage.getItem('theme');
            if (storedTheme === 'light') {
                htmlEl.classList.remove('dark');
                htmlEl.classList.add('light');
                themeToggle.textContent = 'DARK';
            } else {
                 htmlEl.classList.add('dark');
                 themeToggle.textContent = 'LIGHT';
            }

            selectFileType('json');
            showTab('translate', document.querySelector('nav button'));
            loadDatabaseOptions();
            loadGHSPictograms();
            renderSelectedGHSPictograms();
            setupDragAndDrop();

             const defaultLoaded = document.getElementById('file-label').textContent.includes('Standard');
            if(defaultLoaded) {
                document.getElementById('translateBtn').disabled = false;
                 fetch('/api/preview/original')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('originalPreview').srcdoc = data.content;
                        document.getElementById('previewContainer').style.display = 'flex';
                    })
            }

            Split(['#original-container', '#translated-container'], {
                sizes: [50, 50],
                gutterSize: 8,
                cursor: 'col-resize',
                gutterStyle: (dimension, gutterSize) => ({
                    'flex-basis': `${gutterSize}px`,
                }),
                onDrag: () => {
                    const originalIframe = document.getElementById('originalPreview');
                    const translatedIframe = document.getElementById('translatedPreview');
                    originalIframe.style.pointerEvents = 'none';
                    translatedIframe.style.pointerEvents = 'none';
                },
                onDragEnd: () => {
                    const originalIframe = document.getElementById('originalPreview');
                    const translatedIframe = document.getElementById('translatedPreview');
                    originalIframe.style.pointerEvents = 'auto';
                    translatedIframe.style.pointerEvents = 'auto';
                }
            });
            
            // Fix scroll for containers
            const originalContainer = document.getElementById('original-container');
            const translatedContainer = document.getElementById('translated-container');
            if (originalContainer) originalContainer.style.overflow = 'auto';
            if (translatedContainer) translatedContainer.style.overflow = 'auto';

            // Scroll Sync Logic
            let isSyncingScroll = false;

            const syncAllScrolls = (sourceName, scrollTop) => {
                if (isSyncingScroll) return;
                isSyncingScroll = true;
                
                const originalPreview = document.getElementById('originalPreview');
                const translatedPreview = document.getElementById('translatedPreview');
                const originalEditor = document.getElementById('originalEditor');
                const richTextEditor = document.getElementById('richTextEditor');
                
                if (sourceName !== 'originalPreview' && originalPreview.contentWindow) {
                    originalPreview.contentWindow.scrollTo(0, scrollTop);
                }
                if (sourceName !== 'translatedPreview' && translatedPreview.contentWindow) {
                    translatedPreview.contentWindow.scrollTo(0, scrollTop);
                }
                if (sourceName !== 'originalEditor' && originalEditor) {
                    originalEditor.scrollTop = scrollTop;
                }
                if (sourceName !== 'richTextEditor' && richTextEditor) {
                    richTextEditor.scrollTop = scrollTop;
                }
                
                setTimeout(() => { isSyncingScroll = false; }, 30);
            };

            const attachIframeScroll = (iframeId) => {
                const iframe = document.getElementById(iframeId);
                // Try listening on the iframe's document
                if (iframe && iframe.contentDocument) {
                    iframe.contentDocument.addEventListener('scroll', () => {
                        const y = iframe.contentWindow ? iframe.contentWindow.scrollY : iframe.contentDocument.documentElement.scrollTop;
                        syncAllScrolls(iframeId, y);
                    });
                }
            };
            
            document.getElementById('originalPreview').addEventListener('load', () => attachIframeScroll('originalPreview'));
            document.getElementById('translatedPreview').addEventListener('load', () => attachIframeScroll('translatedPreview'));
            
            document.getElementById('originalEditor').addEventListener('scroll', function() {
                syncAllScrolls('originalEditor', this.scrollTop);
            });
            document.getElementById('richTextEditor').addEventListener('scroll', function() {
                syncAllScrolls('richTextEditor', this.scrollTop);
            });
            
            // Protect toolbar focus so execCommand works natively
            document.getElementById('editor-toolbar').addEventListener('mousedown', function(e) {
                if (e.target.closest('button')) {
                    e.preventDefault();
                }
            });

            initResizers();
        });

        // ======================================================
        // Interactive Resizer for Images & Tables
        // ======================================================
        const resizerState = {
            activeEl: null,
            startX: 0, startY: 0,
            startW: 0, startH: 0,
            resizerDiv: null
        };
        
        function initResizers() {
            if (resizerState.resizerDiv) {
                resizerState.resizerDiv.remove();
            }
            const resizer = document.createElement('div');
            resizer.className = 'custom-resizer';
            resizer.style.cssText = 'position:absolute; border:2px dashed #76B82A; display:none; pointer-events:none; z-index:1000; transition: none;';
            const handle = document.createElement('div');
            handle.style.cssText = 'position:absolute; right:-6px; bottom:-6px; width:12px; height:12px; background:#76B82A; border:1px solid #fff; cursor:se-resize; pointer-events:auto; border-radius:50%; box-shadow: 0 0 3px rgba(0,0,0,0.3);';
            resizer.appendChild(handle);
            document.body.appendChild(resizer);
            resizerState.resizerDiv = resizer;
            
            handle.addEventListener('mousedown', initDrag);
            document.addEventListener('mousedown', hideResizerOutside);
            
            setupClickEventsForResizer(document.getElementById('richTextEditor'));
            setupClickEventsForResizer(document.getElementById('originalEditor'));
        }

        function setupClickEventsForResizer(editorEl) {
            editorEl.addEventListener('click', (e) => {
                if (e.target.tagName === 'IMG' || e.target.tagName === 'TABLE') {
                    showResizer(e.target, editorEl);
                }
            });
            window.addEventListener('scroll', updateResizerPos);
            editorEl.addEventListener('scroll', updateResizerPos);
        }

        function showResizer(el, editorEl) {
            resizerState.activeEl = el;
            resizerState.editorEl = editorEl;
            resizerState.resizerDiv.style.display = 'block';
            updateResizerPos();
        }

        function updateResizerPos() {
            if (!resizerState.activeEl || resizerState.resizerDiv.style.display === 'none') return;
            const rect = resizerState.activeEl.getBoundingClientRect();
            // Account for page scroll (since resizer is in document.body)
            resizerState.resizerDiv.style.top = (rect.top + window.scrollY) + 'px';
            resizerState.resizerDiv.style.left = (rect.left + window.scrollX) + 'px';
            resizerState.resizerDiv.style.width = rect.width + 'px';
            resizerState.resizerDiv.style.height = rect.height + 'px';
            
            // Hide if scrolled entirely out of editor view
            const editorRect = resizerState.editorEl.getBoundingClientRect();
            if (rect.bottom < editorRect.top || rect.top > editorRect.bottom) {
                resizerState.resizerDiv.style.display = 'none';
            } else {
                resizerState.resizerDiv.style.display = 'block';
            }
        }

        function hideResizerOutside(e) {
            if (resizerState.resizerDiv && resizerState.resizerDiv.style.display !== 'none') {
                if (e.target !== resizerState.activeEl && e.target !== resizerState.resizerDiv && !resizerState.resizerDiv.contains(e.target)) {
                    resizerState.resizerDiv.style.display = 'none';
                    resizerState.activeEl = null;
                }
            }
        }

        function initDrag(e) {
            e.preventDefault();
            e.stopPropagation();
            resizerState.startX = e.clientX;
            resizerState.startY = e.clientY;
            const style = window.getComputedStyle(resizerState.activeEl);
            resizerState.startW = parseInt(style.width, 10) || resizerState.activeEl.offsetWidth;
            resizerState.startH = parseInt(style.height, 10) || resizerState.activeEl.offsetHeight;
            document.addEventListener('mousemove', doDrag);
            document.addEventListener('mouseup', stopDrag);
        }

        function doDrag(e) {
            const dx = e.clientX - resizerState.startX;
            const dy = e.clientY - resizerState.startY;
            let newW = resizerState.startW + dx;
            let newH = resizerState.startH + dy;
            if (newW < 20) newW = 20;
            if (newH < 20) newH = 20;
            resizerState.activeEl.style.width = newW + 'px';
            resizerState.activeEl.style.height = newH + 'px';
            if (resizerState.activeEl.tagName === 'IMG') {
                resizerState.activeEl.style.maxWidth = 'none';
            }
            updateResizerPos();
            isDirty = true;
        }

        function stopDrag(e) {
            document.removeEventListener('mousemove', doDrag);
            document.removeEventListener('mouseup', stopDrag);
        }


        // ======================================================
        // SCRIPT CONTENT
        // ======================================================

        let currentFile = null;
        let translatedContent = null;
        let currentFileType = 'html';
        let isDirty = false;
        let autoSaveInterval;

        function showTab(tabName, btnElement) {
            document.querySelectorAll('nav button').forEach(tab => tab.classList.remove('tab-active', 'text-minerva-green'));
            if (btnElement) btnElement.classList.add('tab-active', 'text-minerva-green');
            
            document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
            document.getElementById(tabName + '-tab').style.display = 'block';
            
            if (tabName === 'stats') loadStats();
            if (tabName === 'database') searchPhrases();
            if (tabName === 'template') loadTemplateEditor();
            if (tabName === 'mapping') loadMappings();
        }
        
        function selectFileType(type) {
            currentFileType = type;
            ['btnHtml', 'btnPdf', 'btnJson', 'btnXml', 'btnCombined'].forEach(id => {
                const btn = document.getElementById(id);
                if (!btn) return;
                const isActive = id.toLowerCase().includes(type);
                
                // Clear all classes first to be safe
                btn.classList.remove('bg-minerva-hover', 'text-minerva-green', 'bg-minerva-green', 'text-white', 'text-light-text-secondary', 'dark:text-minerva-gray');
                
                if (isActive) {
                    btn.classList.add('bg-minerva-green', 'text-white');
                } else {
                    btn.classList.add('text-light-text-secondary', 'dark:text-minerva-gray');
                }
            });
            
            // Toggle between single and combined file upload
            const singleUpload = document.getElementById('single-file-upload');
            const combinedUpload = document.getElementById('combined-file-upload');
            
            if (type === 'combined') {
                singleUpload.classList.add('hidden');
                combinedUpload.classList.remove('hidden');
            } else {
                singleUpload.classList.remove('hidden');
                combinedUpload.classList.add('hidden');
            }
            
            document.getElementById('main-file-input').accept = `.${type}, .${type.toUpperCase()}`;
        }
        
        // Variables for combined upload
        let selectedXmlFile = null;
        let selectedPdfFile = null;
        
        function handleXmlFileSelect(input) {
            const file = input.files[0];
            if (file) {
                selectedXmlFile = file;
                document.getElementById('xml-file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">📄 ${file.name}</span>`;
                checkCombinedUploadReady();
            }
        }
        
        function handlePdfFileSelect(input) {
            const file = input.files[0];
            if (file) {
                selectedPdfFile = file;
                document.getElementById('pdf-file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">📄 ${file.name}</span>`;
                checkCombinedUploadReady();
            }
        }
        
        function checkCombinedUploadReady() {
            const btn = document.getElementById('combined-upload-btn');
            if (selectedXmlFile && selectedPdfFile) {
                btn.disabled = false;
                btn.classList.remove('opacity-50');
            } else {
                btn.disabled = true;
                btn.classList.add('opacity-50');
            }
        }
        
        async function uploadCombinedFiles() {
            if (!selectedXmlFile || !selectedPdfFile) {
                alert('Bitte sowohl eine XML- als auch eine PDF-Datei auswählen.');
                return;
            }
            
            const formData = new FormData();
            formData.append('xml_file', selectedXmlFile);
            formData.append('pdf_file', selectedPdfFile);
            
            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = 'Lade XML und PDF hoch...';
            
            try {
                const response = await fetch('/api/combined-import', {
                    method: 'POST',
                    body: formData
                });
                
                progressText.textContent = 'Verarbeite Daten...';
                progressFill.style.width = '50%';
                
                const result = await response.json();
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';
                    
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${selectedXmlFile.name}</strong> und <strong>${selectedPdfFile.name}</strong> erfolgreich importiert.</div>`;
                    
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';
                    
                } else {
                    throw new Error(result.error || 'Unbekannter Fehler beim kombinierten Import');
                }
            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }
        
        function handleFileSelect(input) {
            const file = input.files[0];
            if (file) {
                processFile(file);
            }
        }
        
        function setupDragAndDrop() {
            const dropArea = document.getElementById('file-drop-area');
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                }, false);
            });
            
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, () => dropArea.classList.add('border-minerva-green'), false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                 dropArea.addEventListener(eventName, () => dropArea.classList.remove('border-minerva-green'), false);
            });

            dropArea.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if(files.length > 0) {
                    processFile(files[0]);
                }
            }, false);
        }

        function processFile(file) {
            document.getElementById('file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">${file.name}</span>`;
            
            const extension = file.name.split('.').pop().toLowerCase();
            if (['html', 'pdf', 'xml', 'json'].includes(extension)) {
                selectFileType(extension);
            }

            if (currentFileType === 'html') uploadFile(file);
            else if (currentFileType === 'pdf') processPdfFile(file);
            else if (currentFileType === 'xml') processXmlFile(file);
            else if (currentFileType === 'json') processJsonFile(file);
        }
        
        async function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/upload', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ Datei <strong>${result.filename}</strong> geladen.</div>`;
                    currentFile = file.name;
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';
                    document.getElementById('progressSection').style.display = 'none';
                } else {
                     document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ ${result.error}</div>`;
                }
            } catch (error) {
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Upload: ${error.message}</div>`;
            }
        }
        
       async function processGenericFile(file, endpoint) {
            const formData = new FormData();
            formData.append('file', file);

            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            progressFill.style.width = '0%';
            progressText.textContent = `Lade ${currentFileType.toUpperCase()} hoch...`;

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });
                
                progressText.textContent = `Verarbeite ${currentFileType.toUpperCase()}...`;
                progressFill.style.width = '50%';

                const result = await response.json();
                
                if (response.ok) {
                    progressFill.style.width = '100%';
                    progressText.textContent = 'Import erfolgreich!';
                    
                    if (result.is_embedded_xml) {
                        document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> verarbeitet.<br>💡 Eingebettete XML-Datei erkannt und für einen fehlerfreien Import verwendet!</div>`;
                    } else {
                        document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> erfolgreich importiert.</div>`;
                    }
                    
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';

                } else {
                    throw new Error(result.error || `Unbekannter Fehler beim ${currentFileType.toUpperCase()}-Import`);
                }

            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }

        function processPdfFile(file) {
            processGenericFile(file, '/api/pdf/process');
        }

        function processXmlFile(file) {
            processGenericFile(file, '/api/sdscom/process');
        }

        function processJsonFile(file) {
            processGenericFile(file, '/api/import/json');
        }

        async function translateFile() {
            const language = document.getElementById('languageSelect').value;
            const translateBtn = document.getElementById('translateBtn');
            translateBtn.disabled = true;
            translateBtn.innerHTML = '... Übersetze ...';
            document.getElementById('progressSection').style.display = 'block';
            
            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ language, pictograms: selectedPictograms })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('translatedPreview').srcdoc = `<style>body{color:black;}</style>${result.preview}`;
                    translatedContent = result.preview;
                    
                    const stats = result.stats;
                    document.getElementById('totalTexts').textContent = stats.total_texts;
                    document.getElementById('translatedCount').textContent = stats.translated_exact;
                    document.getElementById('notFoundCount').textContent = stats.not_found;
                    
                    const coverage = (stats.translated_exact / stats.total_texts * 100) || 0;
                    document.getElementById('coverageBar').style.width = `${coverage.toFixed(1)}%`;
                     document.getElementById('coverageText').textContent = `${coverage.toFixed(1)}%`;
                    
                    const notFoundList = document.getElementById('notFoundList');
                    const notFoundBadge = document.getElementById('notFoundBadge');
                    notFoundList.innerHTML = '';
                    notFoundBadge.textContent = `${result.not_found.length} UNRESOLVED`;
                    
                    if (result.not_found.length > 0) {
                        result.not_found.forEach(phrase => {
                            const item = document.createElement('div');
                            item.className = 'text-xs p-2 hover:bg-minerva-hover flex justify-between items-center';
                            item.innerHTML = `<span>${phrase.text}</span> <button onclick="showAddModalWithText('${phrase.text.replace(/'/g, "\\'")}')" class="text-minerva-green font-bold">Translate</button>`;
                            notFoundList.appendChild(item);
                        });
                    } else {
                        notFoundList.innerHTML = '<div class="text-center text-minerva-gray p-4">🎉 Alle Phrasen gefunden!</div>';
                    }
                    
                    document.getElementById('downloadNotFoundSection').style.display = 'block';
                    toggleEditor(true);
                    
                } else {
                    alert(`Übersetzungsfehler: ${result.error}`);
                }
                
            } catch (error) {
                alert(`Fehler: ${error.message}`);
            } finally {
                translateBtn.disabled = false;
                translateBtn.innerHTML = 'Übersetzung Starten';
                document.getElementById('progressSection').style.display = 'block';
            }
        }
        
        function downloadHTML() { window.location.href = '/api/download'; }
        
        async function downloadPDF() {
            const btn = document.getElementById('pdfDownloadBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg> Exporting...`;
            
            // Save content from editor if active
            const editor = document.getElementById('richTextEditor');
            if (editor.style.display === 'block') {
                try {
                    await fetch('/api/save/translated', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: editor.innerHTML })
                    });
                } catch (error) {
                    console.error("Failed to save content before PDF export:", error);
                    // Optionally alert the user or stop the export, for now just log it
                }
            }

            fetch('/api/download/pdf')
                .then(response => {
                    if (response.ok) return response.blob();
                    throw new Error('PDF generation failed.');
                })
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `translated_sds.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => alert(`PDF-Fehler: ${error.message}`))
                .finally(() => {
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                });
        }

        // GHS Pictograms
        let allPictograms = [];
        let selectedPictograms = [];

        function openGHSModal() { document.getElementById('ghsModal').classList.add('active'); }
        function closeGHSModal() { document.getElementById('ghsModal').classList.remove('active'); }

        async function loadGHSPictograms() {
            try {
                const response = await fetch('/api/ghs/pictograms');
                allPictograms = await response.json();
                renderGHSPictograms();
            } catch (error) {
                console.error('Fehler beim Laden der Piktogramme.');
            }
        }

        function renderGHSPictograms() {
            const list = document.getElementById('ghsAvailableList');
            if(!list) return;
            list.innerHTML = '';
            
            allPictograms.forEach(p => {
                const isSelected = selectedPictograms.includes(p.code);
                const isDisabled = !isSelected && selectedPictograms.length >= 3;
                
                const item = document.createElement('div');
                item.className = `ghs-pictogram-item border-light-border dark:border-minerva-border ${isSelected ? 'selected border-green-400' : ''} ${isDisabled ? 'disabled' : ''}`;
                item.innerHTML = `<img src="/ghs/${p.code.toLowerCase()}.png" alt="${p.name}"><div class="code text-light-text dark:text-white">${p.code}</div>`;
                if (!isDisabled) {
                    item.onclick = () => toggleGHSSelection(p.code);
                }
                list.appendChild(item);
            });
        }
        
        function toggleGHSSelection(code) {
            const index = selectedPictograms.indexOf(code);
            if (index > -1) selectedPictograms.splice(index, 1);
            else if (selectedPictograms.length < 3) selectedPictograms.push(code);
            renderGHSPictograms();
            renderSelectedGHSPictograms();
        }
        
        function renderSelectedGHSPictograms() {
            const list = document.getElementById('ghsSelectedList');
            const display = document.getElementById('ghsSelectedDisplay');
            if(!list || !display) return;
            list.innerHTML = '';
            display.innerHTML = '';
            document.getElementById('ghsSelectedCount').textContent = selectedPictograms.length;

            for(let i=0; i < 3; i++) {
                const code = selectedPictograms[i];
                const placeholder = document.createElement('div');
                placeholder.className = 'aspect-square bg-light-bg dark:bg-minerva-black border border-light-border dark:border-minerva-border rounded flex items-center justify-center hover:border-minerva-green/40 transition-colors cursor-pointer group';
                if(code) {
                    const pictogram = allPictograms.find(p => p.code === code);
                    placeholder.innerHTML = `<img src="/ghs/${pictogram.code.toLowerCase()}.png" class="p-2">`;
                     const selectedItem = placeholder.cloneNode(true);
                     selectedItem.innerHTML += `<button class="remove-btn" onclick="toggleGHSSelection('${code}')">&times;</button>`;
                    list.appendChild(selectedItem);
                } else {
                     placeholder.innerHTML = '<span class="text-lg text-light-text-secondary dark:text-minerva-gray group-hover:text-minerva-green">+</span>';
                     placeholder.onclick = openGHSModal;
                }
                display.appendChild(placeholder);
            }
        }
        
        // Database functions
        async function loadDatabaseOptions() {
            try {
                const response = await fetch('/api/databases');
                const data = await response.json();
                const select = document.getElementById('databaseSelect');
                select.innerHTML = '';
                for (const key in data.available) {
                    const db = data.available[key];
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = db.name;
                    if (db.active) option.selected = true;
                    select.appendChild(option);
                }
            } catch (error) {
                console.error('Fehler beim Laden der Datenbanken.');
            }
        }
        
        async function handleDatabaseChange(select) {
            const dbKey = select.value;
            await fetch('/api/databases/select', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ database: dbKey })
            });
            loadDatabaseOptions();
        }

        async function searchPhrases(page = 1) {
            const query = document.getElementById('searchInput').value;
            const lang = document.getElementById('searchLanguage').value;
            const sortBy = document.getElementById('sortBy') ? document.getElementById('sortBy').value : 'id_desc';
            const filterEn = document.getElementById('filterEnInput') ? document.getElementById('filterEnInput').value : '';
            
            document.getElementById('resultLangHeader').textContent = lang.toUpperCase();
            const tableBody = document.getElementById('phrasesTable');

            try {
                const response = await fetch('/api/phrases/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ q: query, lang: lang, page: page, sort_by: sortBy, filter_en: filterEn })
                });
                const data = await response.json();

                if (data.error) {
                    tableBody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-red-500">${data.error}</td></tr>`;
                    return;
                }

                const phrases = data.phrases || [];
                tableBody.innerHTML = '';
                if (phrases.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-light-text-secondary dark:text-minerva-gray">Keine Phrasen gefunden</td></tr>';
                    return;
                }
                phrases.forEach(p => {
                    const row = tableBody.insertRow();
                    row.className = "hover:bg-light-bg/50 dark:hover:bg-minerva-hover/50";
                    row.innerHTML = `
                        <td class="w-10">
                            <input type="checkbox" class="phrase-checkbox w-4 h-4 rounded border-gray-300 text-minerva-green focus:ring-minerva-green" value="${p.id}" onchange="updateBulkActions()">
                        </td>
                        <td class="text-light-text-secondary dark:text-minerva-gray">${p.id.substring(0,8)}...</td>
                        <td>${p.en_original || ''}</td>
                        <td>${p.translation || ''}</td>
                        <td class="flex gap-2">
                            <button onclick="showEditModal('${p.id}')">✏️</button>
                            <button onclick="deletePhrase('${p.id}')">🗑️</button>
                        </td>
                    `;
                });
                // Reset selection after search
                resetSelection();
                renderPagination(data.total, data.page, data.per_page);
            } catch (error) {
                tableBody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-red-500">Fehler: ${error.message}</td></tr>`;
            }
        }
        
        // Bulk selection functions
        let selectedPhraseIds = new Set();
        
        function toggleSelectAll() {
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            const checkboxes = document.querySelectorAll('.phrase-checkbox');
            
            if (selectAllCheckbox.checked) {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    selectedPhraseIds.add(checkbox.value);
                });
            } else {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    selectedPhraseIds.delete(checkbox.value);
                });
            }
            updateBulkActions();
        }
        
        function updateBulkActions() {
            const checkboxes = document.querySelectorAll('.phrase-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            
            // Update selected set
            selectedPhraseIds.clear();
            checkboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    selectedPhraseIds.add(checkbox.value);
                }
            });
            
            // Update select all checkbox state
            if (checkboxes.length > 0 && selectedPhraseIds.size === checkboxes.length) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else if (selectedPhraseIds.size > 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
            
            // Show/hide bulk actions
            const bulkActions = document.getElementById('bulkActions');
            const selectedCount = document.getElementById('selectedCount');
            
            if (selectedPhraseIds.size > 0) {
                bulkActions.style.display = 'flex';
                selectedCount.textContent = `${selectedPhraseIds.size} ausgewählt`;
            } else {
                bulkActions.style.display = 'none';
            }
        }
        
        function resetSelection() {
            selectedPhraseIds.clear();
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            }
            const bulkActions = document.getElementById('bulkActions');
            if (bulkActions) {
                bulkActions.style.display = 'none';
            }
        }
        
        async function bulkDeleteSelected() {
            const ids = Array.from(selectedPhraseIds);
            if (ids.length === 0) return;
            
            const confirmed = confirm(`Möchten Sie wirklich ${ids.length} Phrase(n) löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.`);
            
            if (!confirmed) return;
            
            try {
                const response = await fetch('/api/phrases/bulk/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: ids })
                });
                const data = await response.json();
                
                if (data.success) {
                    alert(`${data.deleted_count} Phrase(n) erfolgreich gelöscht.`);
                    searchPhrases(); // Reload the table
                } else {
                    alert(`Fehler: ${data.error}`);
                }
            } catch (error) {
                alert(`Fehler: ${error.message}`);
            }
        }
        
        async function exportPhrases(format) {
            // Get selected IDs or empty array for all
            const ids = Array.from(selectedPhraseIds);
            const lang = document.getElementById('searchLanguage').value;
            
            // Confirm if exporting all (no selection)
            if (ids.length === 0) {
                if (!confirm('Keine Phrasen ausgewählt. Möchten Sie ALLE Phrasen exportieren?')) {
                    return;
                }
            }
            
            try {
                const response = await fetch('/api/phrases/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        ids: ids,
                        format: format,
                        lang: lang
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    alert(`Export-Fehler: ${errorData.error || 'Unbekannter Fehler'}`);
                    return;
                }
                
                // Handle the blob response
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `translations_export.${format}`;
                
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename=([^;]+)/);
                    if (match) filename = match[1];
                }
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                alert(`Export-Fehler: ${error.message}`);
            }
        }

        function renderPagination(total, page, per_page) {
            const paginationContainer = document.getElementById('pagination-container');
            paginationContainer.innerHTML = '';
            const totalPages = Math.ceil(total / per_page);

            for(let i = 1; i <= totalPages; i++) {
                const button = document.createElement('button');
                button.textContent = i;
                button.className = `px-3 py-1 rounded mx-1 ${i === page ? 'bg-minerva-green text-white' : 'bg-light-bg dark:bg-minerva-black'}`;
                button.onclick = () => searchPhrases(i);
                paginationContainer.appendChild(button);
            }
        }

        let modal;
        function showAddModal() {
            if (!modal) modal = document.getElementById('phraseModal');
            document.getElementById('phraseForm').reset();
            document.getElementById('phraseId').value = '';
            document.getElementById('modalTitle').textContent = 'Neue Phrase hinzufügen';
            modal.classList.add('active');
            isDirty = false;
        }
        function showAddModalWithText(text) {
            showAddModal();
            document.getElementById('enText').value = text;
        }

        async function showEditModal(id) {
            if (!modal) modal = document.getElementById('phraseModal');
            const response = await fetch(`/api/phrases/${id}/full`);
            const phrase = await response.json();
            document.getElementById('phraseId').value = phrase.id;
            document.getElementById('enText').value = phrase.en_original || '';
            document.querySelectorAll('[id$="Text"]').forEach(el => {
                const lang = el.id.replace('Text', '');
                if (lang !== 'en') el.value = phrase[`${lang}_original`] || '';
            });
            document.getElementById('modalTitle').textContent = 'Phrase bearbeiten';
            modal.classList.add('active');
            isDirty = false;
        }
        function closeModal() {
            if (!modal) modal = document.getElementById('phraseModal');
            if(isDirty) {
                if(confirm("You have unsaved changes. Are you sure you want to close?")) {
                    modal.classList.remove('active');
                }
            } else {
                modal.classList.remove('active');
            }
        }

        document.addEventListener('DOMContentLoaded', () => {
            modal = document.getElementById('phraseModal');
            document.getElementById('phraseForm').addEventListener('input', () => { isDirty = true; });
            document.getElementById('phraseForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                isDirty = false;
                const id = document.getElementById('phraseId').value;
                const data = { en_original: document.getElementById('enText').value };
                document.querySelectorAll('[id$="Text"]').forEach(el => {
                    const lang = el.id.replace('Text', '');
                    data[`${lang}_original`] = el.value;
                });
                const url = id ? `/api/phrases/${id}` : '/api/phrases';
                const method = id ? 'PUT' : 'POST';
                await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                closeModal();
                searchPhrases();
            });
        });

        async function uploadBulkFile() {
            const fileInput = document.getElementById('bulkFileInput');
            const sourceLang = document.getElementById('bulkSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!fileInput.files || !fileInput.files[0]) {
                statusDiv.innerHTML = '<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Bitte eine TXT-Datei auswaehlen</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="text-blue-400 text-xs p-2 bg-blue-500/10 rounded">Wird hochgeladen...</div>';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('source_lang', sourceLang);

            try {
                const response = await fetch('/api/phrases/bulk/upload', { method: 'POST', body: formData });
                const data = await response.json();
                if (data.success) {
                    statusDiv.innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">&#10003; ${data.created} neue Phrasen erstellt, ${data.updated} aktualisiert (Sprache: ${data.source_language.toUpperCase()})</div>`;
                    fileInput.value = '';
                } else {
                    statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Fehler: ${error.message}</div>`;
            }
        }

        async function applyQuickEdit() {
            const text = document.getElementById('quickEditText').value.trim();
            const sourceLang = document.getElementById('quickSourceLang').value;
            const statusDiv = document.getElementById('bulkStatus');

            if (!text) {
                statusDiv.innerHTML = '<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Bitte Text eingeben</div>';
                return;
            }

            statusDiv.innerHTML = '<div class="text-blue-400 text-xs p-2 bg-blue-500/10 rounded">Wird verarbeitet...</div>';

            try {
                const response = await fetch('/api/phrases/bulk/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, source_lang: sourceLang })
                });
                const data = await response.json();
                if (data.success) {
                    statusDiv.innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">&#10003; ${data.created} neue Phrasen erstellt, ${data.updated} aktualisiert (Sprache: ${data.source_language.toUpperCase()})</div>`;
                    document.getElementById('quickEditText').value = '';
                } else {
                    statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">${data.error}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">Fehler: ${error.message}</div>`;
            }
        }

        async function deletePhrase(id) {
            if (confirm(`Diese Phrase wirklich löschen?`)) {
                await fetch(`/api/phrases/${id}`, { method: 'DELETE' });
                searchPhrases();
            }
        }
        
        // Export document functions
        async function exportDocument(format) {
            const exportBtn = event.target.closest('button');
            const originalText = exportBtn.innerHTML;
            
            // Show loading indicator
            exportBtn.innerHTML = '⏳ Exportiere...';
            exportBtn.disabled = true;
            
            // Save content from editor if active
            const editor = document.getElementById('richTextEditor');
            if (editor.style.display === 'block') {
                try {
                    await fetch('/api/save/translated', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: editor.innerHTML })
                    });
                } catch (error) {
                    console.error("Failed to save content before export:", error);
                }
            }

            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ format: format })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    alert(`Export-Fehler: ${errorData.error || 'Unbekannter Fehler'}`);
                    return;
                }
                
                // Handle the blob response
                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = `translated_document.${format}`;
                
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename=([^;]+)/);
                    if (match) filename = match[1];
                }
                
                // Create download link
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
            } catch (error) {
                alert(`Export-Fehler: ${error.message}`);
            } finally {
                // Restore button
                exportBtn.innerHTML = originalText;
                exportBtn.disabled = false;
            }
        }
        async function loadStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                document.getElementById('dbStats').innerHTML = `
                    <div class="bg-light-bg dark:bg-minerva-card p-4 rounded-lg"><div class="text-3xl font-bold">${data.total_phrases}</div><div class="text-sm text-light-text-secondary dark:text-minerva-gray">Gesamtphrasen</div></div>
                `;

                const langStatsContainer = document.getElementById('langStats');
                langStatsContainer.innerHTML = '';
                Object.entries(data.per_language).forEach(([lang, count]) => {
                    const percentage = (count / data.total_phrases * 100).toFixed(1);
                    langStatsContainer.innerHTML += `
                        <div class="bg-light-bg dark:bg-minerva-card p-4 rounded-lg">
                            <div class="flex justify-between items-baseline">
                                <div class="font-bold text-lg">${lang.toUpperCase()}</div>
                                <div class="text-xl">${count}</div>
                            </div>
                            <div class="w-full bg-light-border dark:bg-minerva-border rounded-full h-2.5 mt-2">
                                <div class="bg-minerva-green h-2.5 rounded-full" style="width: ${percentage}%"></div>
                            </div>
                        </div>
                    `;
                });
            } catch (e) {
                console.error(e)
            }
        }
        
        function toggleEditor(show) {
            const editor = document.getElementById('richTextEditor');
            const originalEditor = document.getElementById('originalEditor');
            const translatedIframe = document.getElementById('translatedPreview');
            const originalIframe = document.getElementById('originalPreview');
            const toolbar = document.getElementById('editor-toolbar');
            const editBtn = document.getElementById('editBtn');
            
            if (show) {
                // Load content into editors
                const originalContent = originalIframe.srcdoc;
                const translatedContent = translatedIframe.srcdoc;
                
                // Add editing CSS to make content fully editable
                const editingCSS = `
                    <style>
                        :root { color-scheme: light; }
                        * { pointer-events: auto !important; cursor: text !important; }
                        body { pointer-events: auto !important; cursor: text !important; }
                        .page { pointer-events: auto !important; }
                        [contenteditable] { pointer-events: auto !important; }
                        [contenteditable]:hover { outline: 1px dashed #76B82A; }
                        /* Keep exact SDS theme classes accessible even in dirty HTML states */
                        .section-title { font-weight: 700; font-size: 10pt; background-color: #e6e6e6; border: 1px solid #000; border-top: 2px solid #000; padding: 4px 8px; margin: 8px 0 0 0; text-decoration: underline; }
                        .subsection-title { font-weight: 700; font-size: 9.5pt; margin: 6px 0 3px 0; }
                        .subsubsection { font-weight: 700; font-size: 9.5pt; text-decoration: underline; margin: 4px 0 2px 0; }
                        .subsubsection { font-weight: 700; font-size: 9.5pt; text-decoration: underline; margin: 4px 0 2px 0; }
                        table { border-collapse: collapse; width: 100%; }
                        th, td { border: 1px solid #000; padding: 3px 5px; }
                        table.sds th { background-color: #F2F2F2; font-weight: 700; }
                    </style>
                `;
                
                // Inject CSS into content
                const processContent = (content) => {
                    let processed = content;
                    if (processed && processed.includes('</head>')) {
                        processed = processed.replace('</head>', editingCSS + '</head>');
                    } else if (processed && processed.includes('<html>')) {
                        processed = '<html><head>' + editingCSS + '</head><body>' + processed.replace(/<html>|<\/html>|<body>|<\/body>/g, '') + '</body></html>';
                    }
                    
                    // Prevent 404 errors for template variables
                    processed = processed.replace(/src=["'][^"']*\{\{[^"']+\}\}[^"']*["']/g, 'data-src="placeholder"');
                    return processed;
                };
                
                originalEditor.innerHTML = processContent(originalContent);
                editor.innerHTML = processContent(translatedContent);
                
                // Show editors, hide iframes
                translatedIframe.style.display = 'none';
                originalIframe.style.display = 'none';
                editor.style.display = 'block';
                originalEditor.style.display = 'block';
                
                // Set caret color for visibility
                editor.style.caretColor = 'black';
                originalEditor.style.caretColor = 'black';

                // Show toolbar
                toolbar.style.display = 'flex';
                
                // Update button text
                editBtn.textContent = '(Beenden)';
                
                startAutoSave();
            } else {
                // Save content back to iframes
                translatedIframe.srcdoc = editor.innerHTML;
                originalIframe.srcdoc = originalEditor.innerHTML;
                
                // Show iframes, hide editors
                translatedIframe.style.display = 'block';
                originalIframe.style.display = 'block';
                editor.style.display = 'none';
                originalEditor.style.display = 'none';

                // Reset caret color
                editor.style.caretColor = '';
                originalEditor.style.caretColor = '';
                
                // Hide toolbar
                toolbar.style.display = 'none';
                
                // Update button text
                editBtn.textContent = '(Bearbeiten)';
                
                stopAutoSave();
            }
        }



        function startAutoSave() {
            if (autoSaveInterval) clearInterval(autoSaveInterval);
            autoSaveInterval = setInterval(autoSaveChanges, 30000);
        }

        function stopAutoSave() {
            clearInterval(autoSaveInterval);
        }

        async function autoSaveChanges() {
            const editor = document.getElementById('richTextEditor');
            const content = editor.innerHTML;
            showSaveStatus('Saving...');
            try {
                const response = await fetch('/api/save/translated', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: content })
                });
                const result = await response.json();
                if(result.success) {
                    showSaveStatus('Saved!');
                } else {
                    showSaveStatus('Error saving!');
                }
            } catch (error) {
                showSaveStatus('Error saving!');
            }
        }

        // Table editing functions
        function applyFormatStyle(styleValue) {
            if (!styleValue) return;
            
            const selection = window.getSelection();
            if (!selection.rangeCount) return;
            
            // Check if there's selected text
            const isSelection = !selection.isCollapsed;
            
            if (isSelection) {
                // Get the selected text range
                const range = selection.getRangeAt(0);
                const selectedText = range.toString();
                
                if (selectedText.length > 0) {
                    // Apply formatting to selected text using span with class
                    const span = document.createElement('span');
                    
                    switch (styleValue) {
                        case 'section-title':
                            span.className = 'section-title';
                            break;
                        case 'subsection-title':
                            span.className = 'subsection-title';
                            break;
                        case 'subsubsection':
                            span.className = 'subsubsection';
                            break;
                        case 'sub-heading':
                            span.className = 'sub-heading';
                            break;
                        case 'sub-heading-u':
                            span.className = 'sub-heading';
                            span.style.textDecoration = 'underline';
                            break;
                        case 'normal-text':
                            // No class, just normal text
                            break;
                        case 'table-text':
                            span.style.fontWeight = 'normal';
                            break;
                        case 'table-header':
                            span.style.fontWeight = 'bold';
                            break;
                    }
                    
                    // Extract content and wrap with span
                    range.surroundContents(span);
                    
                    // Clear selection and place cursor after the span
                    selection.removeAllRanges();
                    
                    // Reset dropdown
                    document.getElementById('formatStyle').value = '';
                    
                    const editor = document.getElementById('richTextEditor');
                    editor.focus();
                    return;
                }
            }
            
            // Fallback: Format as paragraph first to ensure block level container
            document.execCommand('formatBlock', false, 'p');
            
            // Find current paragraph or block node
            const node = findParent(selection.anchorNode, 'P, DIV, H1, H2, H3, H4, H5, H6, LI, TD, TH');
            
            if (node) {
                // Reset styling classes associated with our formats
                node.classList.remove('section-title', 'subsection-title', 'subsubsection', 'sub-heading');
                // Reset inline styles
                node.style.fontWeight = '';
                node.style.textDecoration = '';
                
                switch (styleValue) {
                    case 'section-title':
                        node.className = 'section-title';
                        break;
                    case 'subsection-title':
                        node.className = 'subsection-title';
                        break;
                    case 'subsubsection':
                        node.className = 'subsubsection';
                        break;
                    case 'sub-heading':
                        node.style.fontWeight = 'bold';
                        break;
                    case 'sub-heading-u':
                        node.style.fontWeight = 'bold';
                        node.style.textDecoration = 'underline';
                        break;
                    case 'normal-text':
                        // Resetting classes and styles (already done above) is sufficient for normal text
                        break;
                    case 'table-text':
                        node.style.fontWeight = 'normal';
                        break;
                    case 'table-header':
                        node.style.fontWeight = 'bold';
                        break;
                }
            }
            
            // Reset dropdown to default option visually
            document.getElementById('formatStyle').value = '';
            
            // Focus back on editor to not lose cursor
            const editor = document.getElementById('richTextEditor');
            editor.focus();
        }

        function insertTable() {
            const rows = prompt("Anzahl der Zeilen:", "3");
            const cols = prompt("Anzahl der Spalten:", "3");
            
            if (!rows || !cols) return;
            
            const numRows = parseInt(rows);
            const numCols = parseInt(cols);
            
            if (isNaN(numRows) || isNaN(numCols) || numRows < 1 || numCols < 1) {
                alert("Bitte geben Sie gültige Zahlen ein.");
                return;
            }
            
            const table = document.createElement('table');
            table.className = 'sds';
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            
            const tbody = document.createElement('tbody');
            
            for (let i = 0; i < numRows; i++) {
                const tr = document.createElement('tr');
                for (let j = 0; j < numCols; j++) {
                    const cell = document.createElement(i === 0 ? 'th' : 'td');
                    cell.textContent = i === 0 ? `Header ${j + 1}` : `Cell ${i + 1}-${j + 1}`;
                    cell.style.border = '1px solid #000';
                    cell.style.padding = '3px 5px';
                    cell.style.fontFamily = 'Arial, sans-serif';
                    cell.style.fontSize = '9pt';
                    if (i === 0) {
                        cell.style.backgroundColor = '#F2F2F2';
                        cell.style.fontWeight = '700';
                    }
                    tr.appendChild(cell);
                }
                tbody.appendChild(tr);
            }
            table.appendChild(tbody);
            
            document.execCommand('insertHTML', false, table.outerHTML);
            isDirty = true;
        }

        function mergeTableCells() {
            const selection = window.getSelection();
            
            // Check if there's selected text
            const isSelection = !selection.isCollapsed;
            
            if (isSelection) {
                alert("Bitte setzen Sie den Cursor in eine Zelle (nicht Text markieren), die Sie mit ihrer rechten Nachbarzelle zusammenführen möchten.");
                return;
            }
            
            const currentCell = findParent(selection.anchorNode, 'TH, TD');
            if (!currentCell) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzelle.");
                return;
            }
            
            // Check if there's a next sibling cell in the same row
            const nextCell = currentCell.nextElementSibling;
            if (!nextCell || (nextCell.tagName !== 'TH' && nextCell.tagName !== 'TD')) {
                alert("Keine rechte Nachbarzelle gefunden. Der Cursor muss in einer Zelle sein, die eine rechte Nachbarzelle hat.");
                return;
            }
            
            // Current cell span
            const currentColSpan = parseInt(currentCell.getAttribute('colspan') || 1);
            const nextColSpan = parseInt(nextCell.getAttribute('colspan') || 1);
            
            // Merge text content
            currentCell.innerHTML += ' ' + nextCell.innerHTML;
            
            // Update colspan and remove the next cell
            currentCell.setAttribute('colspan', currentColSpan + nextColSpan);
            nextCell.parentNode.removeChild(nextCell);
            
            isDirty = true;
        }

        function splitTableCell() {
            const selection = window.getSelection();
            const currentCell = findParent(selection.anchorNode, 'TH, TD');
            if (!currentCell) {
                alert("Bitte setzen Sie den Cursor in die zu teilende Zelle.");
                return;
            }
            const currentColSpan = parseInt(currentCell.getAttribute('colspan') || 1);
            if (currentColSpan <= 1) {
                alert("Diese Zelle kann nicht weiter geteilt werden (Colspan ist 1).");
                return;
            }
            
            const newSpan = Math.floor(currentColSpan / 2);
            const remainingSpan = currentColSpan - newSpan;
            
            currentCell.setAttribute('colspan', newSpan);
            
            const newCell = document.createElement(currentCell.tagName);
            newCell.setAttribute('colspan', remainingSpan);
            newCell.innerHTML = '&nbsp;';
            currentCell.parentNode.insertBefore(newCell, currentCell.nextSibling);
        }

        function setColumnWidth() {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            if (!cell) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzelle.");
                return;
            }
            const currentWidth = cell.style.width || cell.getAttribute('width') || '';
            const newWidth = prompt("Neue Spaltenbreite eingeben (z.B. 20%, 150px):", currentWidth);
            
            if (newWidth !== null) {
                cell.style.width = newWidth;
                cell.setAttribute('width', newWidth);
                isDirty = true;
            }
        }

        // SDS Tabellendesign anwenden
        function applySDSTableStyle() {
            const selection = window.getSelection();
            const table = findParent(selection.anchorNode, 'TABLE');
            
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            // Apply SDS table styling
            table.style.borderCollapse = 'collapse';
            table.style.width = '100%';
            table.classList.add('sds');
            
            // Style all cells
            table.querySelectorAll('th, td').forEach(cell => {
                cell.style.border = '1px solid #000';
                cell.style.padding = '3px 5px';
                cell.style.fontFamily = 'Arial, sans-serif';
                cell.style.fontSize = '9pt';
            });
            
            // Style header cells specifically
            table.querySelectorAll('th').forEach(th => {
                th.style.backgroundColor = '#F2F2F2';
                th.style.fontWeight = '700';
                th.style.textAlign = 'left';
            });
            
            // Ensure table has a tbody
            if (!table.querySelector('tbody')) {
                const rows = Array.from(table.querySelectorAll('tr'));
                const tbody = document.createElement('tbody');
                rows.forEach(row => tbody.appendChild(row));
                table.appendChild(tbody);
            }
            
            isDirty = true;
        }

        function promptAndInsertImage() {
            const url = prompt("Bild-URL eingeben (z.B. base64 Daten oder Web-Link):");
            if (!url) return;
            
            const width = prompt("Bildbreite in % oder px (oder leer lassen für Originalgröße):", "100%");
            
            let imgStyle = "max-width: 100%; height: auto;";
            if (width && width.trim() !== '') {
                imgStyle += ` width: ${width.trim()};`;
            }
            
            const imgHtml = `<img src="${url}" style="${imgStyle}" alt="Eingefügtes Bild" />`;
            document.execCommand('insertHTML', false, imgHtml);
        }

        function insertRow() {
            const selection = window.getSelection();
            
            // Check if cursor is in a table
            const table = findParent(selection.anchorNode, 'TABLE');
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            // Get the row count to determine cell count
            const rows = table.querySelectorAll('tr');
            if (rows.length === 0) {
                alert("Die Tabelle hat keine Zeilen.");
                return;
            }
            
            const firstRow = rows[0];
            const cellCount = firstRow.children.length;
            
            // Create new row
            const row = document.createElement('tr');
            for (let i = 0; i < cellCount; i++) {
                const cell = document.createElement('td');
                cell.textContent = 'New Cell';
                cell.style.border = '1px solid #000';
                cell.style.padding = '3px 5px';
                cell.style.fontFamily = 'Arial, sans-serif';
                cell.style.fontSize = '9pt';
                row.appendChild(cell);
            }
            
            // Find current row and insert after it
            const currentRow = findParent(selection.anchorNode, 'TR');
            if (currentRow && currentRow.parentNode) {
                if (currentRow.nextSibling) {
                    currentRow.parentNode.insertBefore(row, currentRow.nextSibling);
                } else {
                    currentRow.parentNode.appendChild(row);
                }
            } else {
                // If no current row found, append to tbody or table
                const tbody = table.querySelector('tbody');
                if (tbody) {
                    tbody.appendChild(row);
                } else {
                    table.appendChild(row);
                }
            }
            
            isDirty = true;
        }

        function insertColumn() {
            const selection = window.getSelection();
            
            // Check if cursor is in a table
            const table = findParent(selection.anchorNode, 'TABLE');
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            // Find current cell to determine insertion position
            const currentCell = findParent(selection.anchorNode, 'TH, TD');
            let insertIndex = -1;
            
            if (currentCell) {
                const row = currentCell.parentNode;
                const cells = Array.from(row.children);
                insertIndex = cells.indexOf(currentCell) + 1;
            }
            
            // Add new cell to each row
            table.querySelectorAll('tr').forEach((row, rowIndex) => {
                const cell = document.createElement(rowIndex === 0 ? 'th' : 'td');
                cell.textContent = rowIndex === 0 ? 'New Header' : 'New Cell';
                cell.style.border = '1px solid #000';
                cell.style.padding = '3px 5px';
                cell.style.fontFamily = 'Arial, sans-serif';
                cell.style.fontSize = '9pt';
                
                if (insertIndex >= 0 && insertIndex < row.children.length) {
                    row.insertBefore(cell, row.children[insertIndex]);
                } else {
                    row.appendChild(cell);
                }
            });
            
            isDirty = true;
        }

        function deleteRow() {
            const selection = window.getSelection();
            
            // Check if cursor is in a table
            const table = findParent(selection.anchorNode, 'TABLE');
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            const row = findParent(selection.anchorNode, 'TR');
            if (!row) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzeile.");
                return;
            }
            
            // Check if table has more than one row
            const rowCount = table.querySelectorAll('tr').length;
            if (rowCount <= 1) {
                alert("Die letzte Zeile kann nicht gelöscht werden. Löschen Sie stattdessen die gesamte Tabelle.");
                return;
            }
            
            row.parentNode.removeChild(row);
            isDirty = true;
        }

        function deleteColumn() {
            const selection = window.getSelection();
            
            // Check if cursor is in a table
            const table = findParent(selection.anchorNode, 'TABLE');
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            const cell = findParent(selection.anchorNode, 'TH, TD');
            if (!cell) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzelle.");
                return;
            }
            
            const row = cell.parentNode;
            const cellIndex = Array.from(row.children).indexOf(cell);
            
            // Check if column has more than one cell in this row
            if (row.children.length <= 1) {
                alert("Die letzte Spalte kann nicht gelöscht werden. Löschen Sie stattdessen die gesamte Tabelle.");
                return;
            }
            
            // Remove cell at this index from all rows
            table.querySelectorAll('tr').forEach(row => {
                if (row.children[cellIndex]) {
                    row.removeChild(row.children[cellIndex]);
                }
            });
            
            isDirty = true;
        }

        function deleteTable() {
            const selection = window.getSelection();
            
            const table = findParent(selection.anchorNode, 'TABLE');
            if (!table) {
                alert("Bitte setzen Sie den Cursor in eine Tabelle.");
                return;
            }
            
            if (confirm("Möchten Sie die gesamte Tabelle wirklich löschen?")) {
                table.parentNode.removeChild(table);
                isDirty = true;
            }
        }

        function changeTableCellBgColor(color) {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            
            if (!cell) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzelle.");
                return;
            }
            
            cell.style.backgroundColor = color;
            isDirty = true;
        }

        function changeTableCellBorderColor(color) {
            const selection = window.getSelection();
            const cell = findParent(selection.anchorNode, 'TH, TD');
            
            if (!cell) {
                alert("Bitte setzen Sie den Cursor in eine Tabellenzelle.");
                return;
            }
            
            cell.style.borderColor = color;
            isDirty = true;
        }

        function findParent(node, tagName) {
            while (node && node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName === tagName) {
                    return node;
                }
                node = node.parentNode;
            }
            return null;
        }

        function showSaveStatus(message) {
            const statusIndicator = document.getElementById('save-status-indicator');
            statusIndicator.textContent = message;
            statusIndicator.classList.add('visible');
            setTimeout(() => {
                statusIndicator.classList.remove('visible');
            }, 3000);
        }

        // ======================================================
        // TEMPLATE EDITOR LOGIC
        // ======================================================
        async function loadTemplateEditor() {
            try {
                const res = await fetch('/api/template');
                const data = await res.json();
                if (data.success) {
                    document.getElementById('templateCodeEditor').value = data.content;
                    // Update preview after loading
                    setTimeout(updatePreview, 100);
                } else {
                    alert('Fehler beim Laden des Templates: ' + data.error);
                }
            } catch (err) {
                console.error(err);
                alert('Netzwerkfehler beim Laden des Templates.');
            }
        }

        async function saveTemplate() {
            const content = document.getElementById('templateCodeEditor').value;
            try {
                const res = await fetch('/api/template/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                const data = await res.json();
                if (data.success) {
                    alert('Template erfolgreich gespeichert!');
                    updatePreview();
                } else {
                    alert('Fehler beim Speichern: ' + data.error);
                }
            } catch (err) {
                console.error(err);
                alert('Netzwerkfehler beim Speichern.');
            }
        }

        async function resetTemplate() {
            if (!confirm('Möchten Sie das Template wirklich auf den Originalzustand zurücksetzen? Alle Ihre Änderungen gehen verloren!')) return;
            try {
                const res = await fetch('/api/template/reset', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    document.getElementById('templateCodeEditor').value = data.content;
                    alert('Template wurde erfolgreich zurückgesetzt.');
                    updatePreview();
                } else {
                    alert('Fehler beim Zurücksetzen: ' + data.error);
                }
            } catch (err) {
                console.error(err);
                alert('Netzwerkfehler beim Zurücksetzen.');
            }
        }

        function exportTemplate() {
            const content = document.getElementById('templateCodeEditor').value;
            const blob = new Blob([content], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'layout_template_export.html';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        function importTemplateFile(input) {
            const file = input.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById('templateCodeEditor').value = e.target.result;
                input.value = ''; // Reset file input
                updatePreview();
            };
            reader.readAsText(file);
        }

        // ======================================================
        // WYSIWYG EDITOR FUNCTIONS
        // ======================================================
        let currentEditorMode = 'code';
        let wysiwygSyncTimeout = null;
        
        function switchEditorMode(mode) {
            currentEditorMode = mode;
            const codeEditor = document.getElementById('templateCodeEditor');
            const wysiwygEditor = document.getElementById('wysiwygEditor');
            const codeTab = document.getElementById('codeEditorTab');
            const wysiwygTab = document.getElementById('wysiwygEditorTab');
            
            if (mode === 'code') {
                codeEditor.style.display = 'block';
                wysiwygEditor.style.display = 'none';
                codeTab.classList.add('border-minerva-green', 'text-minerva-green');
                codeTab.classList.remove('border-transparent', 'text-light-text-secondary', 'dark:text-minerva-gray');
                wysiwygTab.classList.remove('border-minerva-green', 'text-minerva-green');
                wysiwygTab.classList.add('border-transparent', 'text-light-text-secondary', 'dark:text-minerva-gray');
            } else {
                // Sync code to WYSIWYG before showing
                wysiwygEditor.innerHTML = codeEditor.value;
                codeEditor.style.display = 'none';
                wysiwygEditor.style.display = 'block';
                wysiwygTab.classList.add('border-minerva-green', 'text-minerva-green');
                wysiwygTab.classList.remove('border-transparent', 'text-light-text-secondary', 'dark:text-minerva-gray');
                codeTab.classList.remove('border-minerva-green', 'text-minerva-green');
                codeTab.classList.add('border-transparent', 'text-light-text-secondary', 'dark:text-minerva-gray');
            }
            updatePreview();
        }
        
        function toggleEditorMode() {
            const newMode = currentEditorMode === 'code' ? 'wysiwyg' : 'code';
            switchEditorMode(newMode);
        }
        
        function syncCodeToPreview() {
            // Debounce the preview update
            clearTimeout(wysiwygSyncTimeout);
            wysiwygSyncTimeout = setTimeout(() => {
                updatePreview();
            }, 500);
        }
        
        function syncWysiwygToCode() {
            const wysiwygEditor = document.getElementById('wysiwygEditor');
            const codeEditor = document.getElementById('templateCodeEditor');
            codeEditor.value = wysiwygEditor.innerHTML;
            
            // Debounce the preview update
            clearTimeout(wysiwygSyncTimeout);
            wysiwygSyncTimeout = setTimeout(() => {
                updatePreview();
            }, 500);
        }
        
        function updatePreview() {
            const codeEditor = document.getElementById('templateCodeEditor');
            const wysiwygEditor = document.getElementById('wysiwygEditor');
            const previewFrame = document.getElementById('templatePreview');
            
            if (!previewFrame) return;
            
            let content;
            if (currentEditorMode === 'code') {
                content = codeEditor.value;
            } else {
                content = wysiwygEditor.innerHTML;
            }
            
            // Prevent 404 errors in the template preview for Jinja tags
            let previewContent = content.replace(/src=["'][^"']*\{\{[^"']+\}\}[^"']*["']/g, 'data-src="placeholder"');
            
            const previewDoc = previewFrame.contentDocument || previewFrame.contentWindow.document;
            previewDoc.open();
            previewDoc.write(previewContent);
            previewDoc.close();
        }
        
        // ======================================================
        // MAPPING FUNCTIONS
        // ======================================================
        let mappingsData = [];
        
        // Template field to source field mappings (defined in code)
        const defaultMappings = [
            { templateVar: 'section_1.product_name', sourceField: 'Product/Name', section: 'section_1', status: 'active' },
            { templateVar: 'section_1.supplier', sourceField: 'Supplier/Name', section: 'section_1', status: 'active' },
            { templateVar: 'section_1.emergency_phone', sourceField: 'Supplier/EmergencyPhone', section: 'section_1', status: 'active' },
            { templateVar: 'section_2.hazard_statements', sourceField: 'Hazards/HazardStatement', section: 'section_2', status: 'active' },
            { templateVar: 'section_2.precautionary_statements', sourceField: 'Hazards/PrecautionaryStatement', section: 'section_2', status: 'active' },
            { templateVar: 'section_2.ghs_pictograms', sourceField: 'Hazards/GhsPictogram', section: 'section_2', status: 'active' },
            { templateVar: 'section_3.mixture_components', sourceField: 'Composition/Component', section: 'section_3', status: 'active' },
            { templateVar: 'section_4.first_aid_inhalation', sourceField: 'FirstAid/Inhalation', section: 'section_4', status: 'active' },
            { templateVar: 'section_4.first_aid_skin', sourceField: 'FirstAid/SkinContact', section: 'section_4', status: 'active' },
            { templateVar: 'section_4.first_aid_eyes', sourceField: 'FirstAid/EyeContact', section: 'section_4', status: 'active' },
            { templateVar: 'section_4.first_aid_ingestion', sourceField: 'FirstAid/Ingestion', section: 'section_4', status: 'active' },
            { templateVar: 'section_5.extinguishing_media', sourceField: 'Firefighting/ExtinguishingMedia', section: 'section_5', status: 'active' },
            { templateVar: 'section_6.environmental_precautions', sourceField: 'Release/EnvironmentalPrecautions', section: 'section_6', status: 'active' },
            { templateVar: 'section_7.safe_handling', sourceField: 'Handling/SafeHandling', section: 'section_7', status: 'active' },
            { templateVar: 'section_7.storage', sourceField: 'Storage/Conditions', section: 'section_7', status: 'active' },
            { templateVar: 'section_8.ppe', sourceField: 'Exposure/PPE', section: 'section_8', status: 'active' },
            { templateVar: 'section_9.physical_state', sourceField: 'PhysicalChem/State', section: 'section_9', status: 'active' },
            { templateVar: 'section_9.melting_point', sourceField: 'PhysicalChem/MeltingPoint', section: 'section_9', status: 'active' },
            { templateVar: 'section_9.boiling_point', sourceField: 'PhysicalChem/BoilingPoint', section: 'section_9', status: 'active' },
            { templateVar: 'section_10.stability', sourceField: 'StabilityReactivity/Stable', section: 'section_10', status: 'active' },
            { templateVar: 'section_11.acute_toxicity', sourceField: 'Toxicology/AcuteToxicity', section: 'section_11', status: 'active' },
            { templateVar: 'section_12.environmental_fate', sourceField: 'Environmental/EnvironmentalFate', section: 'section_12', status: 'active' },
            { templateVar: 'section_13.disposal', sourceField: 'Disposal/WasteCode', section: 'section_13', status: 'active' },
            { templateVar: 'section_14.un_number', sourceField: 'Transport/UNNumber', section: 'section_14', status: 'active' },
            { templateVar: 'section_14.transport_class', sourceField: 'Transport/Class', section: 'section_14', status: 'active' },
            { templateVar: 'section_15.regulatory_info', sourceField: 'Regulatory/Information', section: 'section_15', status: 'active' },
            { templateVar: 'section_16.revision_date', sourceField: 'Document/RevisionDate', section: 'section_16', status: 'active' },
            { templateVar: 'section_16.revision_history', sourceField: 'Document/RevisionHistory', section: 'section_16', status: 'active' }
        ];
        
        async function loadMappings() {
            try {
                // First try to load from server
                const res = await fetch('/api/mappings');
                const data = await res.json();
                if (data.success && data.mappings && data.mappings.length > 0) {
                    mappingsData = data.mappings;
                } else {
                    // Use default mappings if none exist
                    mappingsData = defaultMappings;
                }
            } catch (e) {
                console.log('Using default mappings');
                mappingsData = defaultMappings;
            }
            renderMappings();
        }
        
        function renderMappings() {
            const sectionFilter = document.getElementById('mappingSectionFilter')?.value || 'all';
            const searchTerm = document.getElementById('mappingSearch')?.value.toLowerCase() || '';
            
            let filtered = mappingsData.filter(m => {
                const matchesSection = sectionFilter === 'all' || m.section === sectionFilter;
                const matchesSearch = m.templateVar.toLowerCase().includes(searchTerm) || 
                                     m.sourceField.toLowerCase().includes(searchTerm);
                return matchesSection && matchesSearch;
            });
            
            const tbody = document.getElementById('mappingTableBody');
            if (!tbody) return;
            
            tbody.innerHTML = filtered.map((m, idx) => `
                <tr class="border-b border-light-border dark:border-minerva-border hover:bg-light-bg dark:hover:bg-minerva-black">
                    <td class="p-3 text-light-text dark:text-gray-300 font-mono text-xs">${escapeHtml(m.templateVar)}</td>
                    <td class="p-3 text-light-text dark:text-gray-300"><input type="text" value="${escapeHtml(m.sourceField)}" 
                        onchange="updateMapping(${mappingsData.indexOf(m)}, 'sourceField', this.value)"
                        class="bg-transparent border border-light-border dark:border-minerva-border rounded px-2 py-1 text-sm w-full"></td>
                    <td class="p-3 text-light-text-secondary dark:text-minerva-gray text-xs">${escapeHtml(m.example || '-')}</td>
                    <td class="p-3">
                        <span class="px-2 py-1 rounded text-xs font-semibold ${m.status === 'active' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}">
                            ${m.status === 'active' ? 'Aktiv' : 'Inaktiv'}
                        </span>
                    </td>
                    <td class="p-3">
                        <button onclick="toggleMappingStatus(${mappingsData.indexOf(m)})" class="text-xs px-2 py-1 rounded ${m.status === 'active' ? 'bg-red-500/20 text-red-500' : 'bg-green-500/20 text-green-500'}">
                            ${m.status === 'active' ? 'Deaktivieren' : 'Aktivieren'}
                        </button>
                    </td>
                </tr>
            `).join('');
            
            if (filtered.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-light-text-secondary dark:text-minerva-gray">Keine Mappings gefunden</td></tr>`;
            }
        }
        
        function filterMappings() {
            renderMappings();
        }
        
        function updateMapping(index, field, value) {
            if (mappingsData[index]) {
                mappingsData[index][field] = value;
            }
        }
        
        function toggleMappingStatus(index) {
            if (mappingsData[index]) {
                mappingsData[index].status = mappingsData[index].status === 'active' ? 'inactive' : 'active';
                renderMappings();
            }
        }
        
        function addNewMapping() {
            const templateVar = document.getElementById('newMappingTemplateVar').value.trim();
            const sourceField = document.getElementById('newMappingSourceField').value.trim();
            
            if (!templateVar || !sourceField) {
                alert('Bitte beide Felder ausfüllen');
                return;
            }
            
            // Extract section from template variable
            const sectionMatch = templateVar.match(/^section_\d+/);
            const section = sectionMatch ? sectionMatch[0] : 'section_1';
            
            mappingsData.push({
                templateVar,
                sourceField,
                section,
                status: 'active',
                example: ''
            });
            
            document.getElementById('newMappingTemplateVar').value = '';
            document.getElementById('newMappingSourceField').value = '';
            
            renderMappings();
        }
        
        async function saveMappings() {
            try {
                const res = await fetch('/api/mappings/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mappings: mappingsData })
                });
                const data = await res.json();
                if (data.success) {
                    alert('Mappings erfolgreich gespeichert!');
                } else {
                    alert('Fehler beim Speichern: ' + data.error);
                }
            } catch (e) {
                console.error(e);
                // Save to localStorage as fallback
                localStorage.setItem('sds_mappings', JSON.stringify(mappingsData));
                alert('Mappings im lokalen Speicher gespeichert (Fallback)');
            }
        }
        
        async function refreshMappings() {
            await loadMappings();
            alert('Mappings aktualisiert');
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        } 