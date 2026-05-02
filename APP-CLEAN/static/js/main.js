
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

            // Härtung: Prüfen ob Element existiert, um JS-Abstürze beim Laden zu verhindern
            const fileLabel = document.getElementById('file-label');
            const isDefaultOrEmpty = !fileLabel || fileLabel.textContent.includes('Standard') || fileLabel.textContent.includes('Keine') || fileLabel.textContent.trim() === '';
            
            if(isDefaultOrEmpty) {
                const translateBtn = document.getElementById('translateBtn');
                if (translateBtn) translateBtn.disabled = false;
                
                fetch('/api/preview/original')
                    .then(response => response.ok ? response.json() : { content: '' })
                    .then(data => {
                        const origPreview = document.getElementById('originalPreview');
                        const prevContainer = document.getElementById('previewContainer');
                        if (data.content && origPreview) origPreview.srcdoc = data.content;
                        if (data.content && prevContainer) prevContainer.style.display = 'flex';
                    })
                    .catch(e => console.warn('Preview load failed:', e));
            }

            try {
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
                        if (originalIframe) originalIframe.style.pointerEvents = 'none';
                        if (translatedIframe) translatedIframe.style.pointerEvents = 'none';
                    },
                    onDragEnd: () => {
                        const originalIframe = document.getElementById('originalPreview');
                        const translatedIframe = document.getElementById('translatedPreview');
                        if (originalIframe) originalIframe.style.pointerEvents = 'auto';
                        if (translatedIframe) translatedIframe.style.pointerEvents = 'auto';
                    }
                });
            } catch (e) {
                console.warn('Split.js initialization skipped/failed:', e);
            }
            
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
                
                if (sourceName !== 'originalPreview' && originalPreview.contentWindow) {
                    originalPreview.contentWindow.scrollTo(0, scrollTop);
                }
                if (sourceName !== 'translatedPreview' && translatedPreview.contentWindow) {
                    translatedPreview.contentWindow.scrollTo(0, scrollTop);
                }
                
                if (typeof tinymce !== 'undefined') {
                    const origEd = tinymce.get('originalEditor');
                    if (origEd && sourceName !== 'originalEditor') {
                        origEd.getWin().scrollTo(0, scrollTop);
                    }
                    const transEd = tinymce.get('richTextEditor');
                    if (transEd && sourceName !== 'richTextEditor') {
                        transEd.getWin().scrollTo(0, scrollTop);
                    }
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
            
            // Initialize Terminal Logging
            initTerminalLogging();
            
            // Ensure PDF Engine Dropdown is visible (bypasses HTML caching issues)
            injectPdfEngineDropdown();
        });

        function injectPdfEngineDropdown() {
            const existingDropdown = document.getElementById('pdf-engine-toggle');
            const optionsHTML = `
                <option value="chandra">💎 Chandra / Datalab (Perfekte Tabellen & Scans via VLM)</option>
                <option value="opendataloader">KI / OpenDataLoader (präzise, hochkomplexe Layouts)</option>
                <option value="standard">Standard (schnell, reguläre Tabellen)</option>
            `;
            
            if (existingDropdown) {
                // Falls das Dropdown schon im HTML existiert, erzwingen wir das Update
                if (!existingDropdown.innerHTML.includes('chandra')) {
                    existingDropdown.innerHTML = optionsHTML;
                    const desc = existingDropdown.nextElementSibling;
                    if (desc && desc.tagName === 'P') {
                        desc.innerHTML = 'Wähle "Chandra / Datalab" für bestmögliche Erkennung bei eingescannten PDFs oder extrem komplexen Tabellen.';
                    }
                }
                return;
            }

            const uploadStatus = document.getElementById('uploadStatus');
            if (uploadStatus && uploadStatus.parentNode) {
                const wrapper = document.createElement('div');
                wrapper.className = 'mt-4 mb-2 p-4 border border-light-border dark:border-minerva-border rounded-lg bg-light-bg/50 dark:bg-minerva-black/30';
                wrapper.innerHTML = `
                    <label class="text-xs text-light-text-secondary dark:text-minerva-gray font-bold uppercase block mb-2">
                        📄 PDF Extraktions-Engine
                    </label>
                    <select id="pdf-engine-toggle" class="w-full bg-white dark:bg-minerva-black border border-light-border dark:border-minerva-border rounded p-2 text-sm text-light-text dark:text-white focus:outline-none focus:border-minerva-green transition-colors cursor-pointer shadow-sm">
                        ${optionsHTML}
                    </select>
                    <p class="text-[10px] text-light-text-secondary dark:text-minerva-gray mt-2 leading-relaxed">
                        Wähle "Chandra / Datalab" für bestmögliche Erkennung bei eingescannten PDFs oder extrem komplexen Tabellen.
                    </p>
                `;
                uploadStatus.parentNode.insertBefore(wrapper, uploadStatus);
            }
        }

        // ======================================================
        // TERMINAL LOGIC
        // ======================================================
        let lastLogCount = 0;
        
        function initTerminalLogging() {
            const terminalOutput = document.getElementById('terminal-output');
            
            // Intercept frontend console
            const originalLog = console.log;
            const originalWarn = console.warn;
            const originalError = console.error;

            function appendToTerminal(message, type = 'info') {
                if (!terminalOutput) return;
                const logEl = document.createElement('div');
                const timestamp = new Date().toLocaleTimeString();
                let colorClass = 'text-gray-300';
                if (type === 'warn') colorClass = 'text-yellow-400';
                if (type === 'error') colorClass = 'text-red-400';
                logEl.className = `font-mono text-xs ${colorClass} break-words mb-1`;
                logEl.textContent = `[${timestamp}] [FRONTEND] ${message}`;
                terminalOutput.appendChild(logEl);
                terminalOutput.scrollTop = terminalOutput.scrollHeight;
            }

            console.log = function(...args) {
                originalLog.apply(console, args);
                appendToTerminal(args.map(a => typeof a === 'object' ? JSON.stringify(a) : a).join(' '), 'info');
            };

            console.warn = function(...args) {
                originalWarn.apply(console, args);
                appendToTerminal(args.map(a => typeof a === 'object' ? JSON.stringify(a) : a).join(' '), 'warn');
            };

            console.error = function(...args) {
                originalError.apply(console, args);
                appendToTerminal(args.map(a => typeof a === 'object' ? JSON.stringify(a) : a).join(' '), 'error');
            };

            // Poll backend logs
            setInterval(() => {
                fetch('/api/logs')
                    .then(res => res.json())
                    .then(data => {
                        if (data.logs && data.logs.length > lastLogCount) {
                            if (!terminalOutput) return;
                            const newLogs = data.logs.slice(lastLogCount);
                            newLogs.forEach(log => {
                                const logEl = document.createElement('div');
                                logEl.className = 'font-mono text-xs text-green-400 break-words mb-1';
                                if (log.includes(' - ERROR - ') || log.includes(' - WARNING - ') || log.includes(' - CRITICAL - ')) {
                                    logEl.classList.remove('text-green-400');
                                    logEl.classList.add(log.includes('ERROR') || log.includes('CRITICAL') ? 'text-red-400' : 'text-yellow-400');
                                }
                                logEl.textContent = `[BACKEND] ${log}`;
                                terminalOutput.appendChild(logEl);
                            });
                            lastLogCount = data.logs.length;
                            terminalOutput.scrollTop = terminalOutput.scrollHeight;
                        } else if (data.logs && data.logs.length < lastLogCount) {
                            // Backend restarted or buffer rolled over
                            lastLogCount = 0;
                        }
                    })
                    .catch(err => { /* fail silently for polling */ });
            }, 1000);
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
            if (tabName === 'library') loadLibrary();
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
        
        // Variable for single file upload (new)
        let selectedSingleFile = null;
        let currentSingleFileType = null;
        
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
        
        function startSimulatedProgress(progressFill, progressText, engine) {
            let progress = 0;
            progressFill.style.width = '0%';
            progressFill.style.transition = 'width 1s linear';
            
            const isChandra = engine === 'chandra';
            
            if (isChandra) {
                progressText.innerHTML = '💎 Chandra VLM analysiert das Dokument...<br><span class="text-[10px] font-normal opacity-80">Das Modell verarbeitet die Seiten (Dauer: ca. 30-60 Sekunden).</span>';
            } else {
                progressText.innerHTML = 'Lade Dateien hoch und verarbeite...';
            }
            
            return setInterval(() => {
                const remaining = 95 - progress;
                let step = isChandra ? (remaining * 0.04) : (remaining * 0.15);
                if (step < 0.1) step = 0.1;
                
                progress += step;
                if (progress > 95) progress = 95;
                
                progressFill.style.width = `${progress}%`;
                
                if (isChandra) {
                    if (progress > 40 && progress < 75 && !progressText.innerHTML.includes('Tabellenstrukturen')) {
                         progressText.innerHTML = '💎 Chandra extrahiert komplexe Tabellenstrukturen...<br><span class="text-[10px] font-normal opacity-80">Bitte haben Sie noch etwas Geduld.</span>';
                    } else if (progress > 75 && !progressText.innerHTML.includes('formatiert')) {
                         progressText.innerHTML = '💎 Chandra formatiert die JSON-Ausgabe...<br><span class="text-[10px] font-normal opacity-80">Gleich geschafft!</span>';
                    }
                }
            }, 1000);
        }
        
        async function uploadCombinedFiles() {
            if (!selectedXmlFile || !selectedPdfFile) {
                alert('Bitte sowohl eine XML- als auch eine PDF-Datei auswählen.');
                return;
            }
            
            const formData = new FormData();
            formData.append('xml_file', selectedXmlFile);
            formData.append('pdf_file', selectedPdfFile);
            
            // Hole die Auswahl der PDF-Engine (falls vorhanden, sonst Fallback auf Standard)
            const engineToggle = document.getElementById('pdf-engine-toggle');
            const selectedEngine = engineToggle ? engineToggle.value : 'standard';
            formData.append('pdf_engine', selectedEngine);
            
            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            const simInterval = startSimulatedProgress(progressFill, progressText, selectedEngine);
            
            try {
                const response = await fetch('/api/combined-import', {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(simInterval);
                progressFill.style.transition = 'width 0.3s ease';
                
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
                clearInterval(simInterval);
                progressText.textContent = 'Import fehlgeschlagen!';
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }
        
        function handleFileSelect(input) {
            const file = input.files[0];
            if (file) {
                selectFileForImport(file);
            }
        }
        
        function selectFileForImport(file) {
            selectedSingleFile = file;
            currentSingleFileType = currentFileType;
            
            document.getElementById('file-label').innerHTML = `<span class="text-light-text dark:text-white font-bold">📄 ${file.name}</span>`;
            
            // Enable import button
            const btn = document.getElementById('single-upload-btn');
            btn.disabled = false;
            btn.classList.remove('opacity-50');
            
            document.getElementById('uploadStatus').innerHTML = `<div class="text-blue-500 text-xs p-2 bg-blue-500/10 rounded">📄 <strong>${file.name}</strong> ausgewählt - klicke "Datei Importieren" um fortzufahren</div>`;
        }
        
        async function uploadSingleFile() {
            if (!selectedSingleFile) {
                alert('Bitte wähle zunächst eine Datei aus.');
                return;
            }
            
            const file = selectedSingleFile;
            const fileType = currentSingleFileType;
            
            try {
                if (fileType === 'html') {
                    await importHtmlFile(file);
                } else if (fileType === 'pdf') {
                    await importPdfFile(file);
                } else if (fileType === 'xml') {
                    await importXmlFile(file);
                } else if (fileType === 'json') {
                    await importJsonFile(file);
                }
                
                
                document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> erfolgreich importiert.</div>`;
                
                // Reset for next file
                selectedSingleFile = null;
                document.getElementById('single-upload-btn').disabled = true;
                document.getElementById('main-file-input').value = '';
                
            } catch (error) {
                document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler beim Import: ${error.message}</div>`;
            }
        }
        
        async function importHtmlFile(file) {
            return importFileWithEndpoint(file, '/api/upload', 'html');
        }
        
        async function importPdfFile(file) {
            return importFileWithEndpoint(file, '/api/pdf/process', 'pdf');
        }
        
        async function importXmlFile(file) {
            return importFileWithEndpoint(file, '/api/sdscom/process', 'xml');
        }
        
        async function importJsonFile(file) {
            return importFileWithEndpoint(file, '/api/import/json', 'json');
        }
        
        async function importFileWithEndpoint(file, endpoint, type) {
            const formData = new FormData();
            formData.append('file', file);
            
            // Hole die Auswahl der PDF-Engine
            const engineToggle = document.getElementById('pdf-engine-toggle');
            const selectedEngine = engineToggle ? engineToggle.value : 'standard';
            formData.append('pdf_engine', selectedEngine);
            
            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            const simInterval = startSimulatedProgress(progressFill, progressText, selectedEngine);
            
            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || `Fehler beim ${type.toUpperCase()}-Import`);
                }
                
                progressFill.style.width = '100%';
                progressText.textContent = 'Import erfolgreich!';
                
                if (result.is_embedded_xml) {
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> verarbeitet.<br>💡 Eingebettete XML-Datei erkannt und für einen fehlerfreien Import verwendet!</div>`;
                } else {
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ <strong>${file.name}</strong> erfolgreich importiert.</div>`;
                }
                
                currentFile = file.name;
                document.getElementById('originalPreview').srcdoc = result.preview;
                document.getElementById('previewContainer').style.display = 'flex';
                document.getElementById('translateBtn').disabled = false;
                document.getElementById('translatedPreview').srcdoc = '';
            } catch (error) {
                progressText.textContent = 'Import fehlgeschlagen!';
                throw error;
            } finally {
                clearInterval(simInterval);
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
                    const file = files[0];
                    const extension = file.name.split('.').pop().toLowerCase();
                    if (['html', 'pdf', 'xml', 'json'].includes(extension)) {
                        selectFileType(extension);
                        selectFileForImport(file);
                    } else {
                        alert('Bitte verwende eine HTML, PDF, XML oder JSON Datei.');
                    }
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
            
            // Hole die Auswahl der PDF-Engine
            const engineToggle = document.getElementById('pdf-engine-toggle');
            const selectedEngine = engineToggle ? engineToggle.value : 'standard';
            formData.append('pdf_engine', selectedEngine);

            const progressSection = document.getElementById('progressSection');
            const progressFill = document.getElementById('coverageBar');
            const progressText = document.getElementById('coverageText');
            
            progressSection.style.display = 'block';
            const simInterval = startSimulatedProgress(progressFill, progressText, selectedEngine);

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });
                
                clearInterval(simInterval);
                progressFill.style.transition = 'width 0.3s ease';

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
                clearInterval(simInterval);
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
            // Save manually edited original content before translating
            let originalContentToSave = '';
            const originalWrapper = document.getElementById('originalEditorWrapper');
            
            if (originalWrapper && originalWrapper.style.display === 'block' && typeof tinymce !== 'undefined' && tinymce.get('originalEditor')) {
                const bodyHtml = tinymce.get('originalEditor').getContent();
                originalContentToSave = restoreFullHtml(bodyHtml, 'original');
            } else {
                const iframe = document.getElementById('originalPreview');
                originalContentToSave = iframe.srcdoc || (iframe.contentDocument ? iframe.contentDocument.documentElement.outerHTML : '');
            }
            
            if (originalContentToSave) {
                try {
                    await fetch('/api/save/original', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: originalContentToSave })
                    });
                } catch (e) {
                    console.error("Failed to save original document prior to translation:", e);
                }
            }

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
        
        async function downloadHTML() { 
            let currentContent = '';
            const editorWrapper = document.getElementById('translatedEditorWrapper');
            if (editorWrapper && editorWrapper.style.display === 'block' && typeof tinymce !== 'undefined' && tinymce.get('richTextEditor')) {
                const bodyHtml = tinymce.get('richTextEditor').getContent();
                currentContent = restoreFullHtml(bodyHtml, 'translated');
            } else {
                const iframe = document.getElementById('translatedPreview');
                currentContent = iframe.srcdoc || (iframe.contentDocument ? iframe.contentDocument.documentElement.outerHTML : '');
            }
            
            if (currentContent) {
                try {
                    await fetch('/api/save/translated', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ content: currentContent })
                    });
                } catch (e) {
                    console.error("Failed to save content before export:", e);
                }
            }
            window.location.href = '/api/download'; 
        }
        
        async function downloadPDF() {
            const btn = document.getElementById('pdfDownloadBtn');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg> Exporting...`;
            
            let currentContent = '';
            const editorWrapper = document.getElementById('translatedEditorWrapper');
            if (editorWrapper && editorWrapper.style.display === 'block' && typeof tinymce !== 'undefined' && tinymce.get('richTextEditor')) {
                const bodyHtml = tinymce.get('richTextEditor').getContent();
                currentContent = restoreFullHtml(bodyHtml, 'translated');
            } else {
                const iframe = document.getElementById('translatedPreview');
                currentContent = iframe.srcdoc || (iframe.contentDocument ? iframe.contentDocument.documentElement.outerHTML : '');
            }

            fetch('/api/download/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ edited_content: currentContent })
            })
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
                const selects = document.querySelectorAll('.database-select');
                selects.forEach(select => {
                    select.innerHTML = '';
                    for (const key in data.available) {
                        const db = data.available[key];
                        const option = document.createElement('option');
                        option.value = key;
                        option.textContent = db.name;
                        if (db.active) option.selected = true;
                        select.appendChild(option);
                    }
                });
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
                try {
                    const response = await fetch(`/api/phrases/${id}`, { method: 'DELETE' });
                    if (response.ok) {
                        searchPhrases();
                    } else {
                        alert('Fehler: Die Phrase konnte nicht gelöscht werden.');
                    }
                } catch (error) {
                    alert(`Netzwerkfehler: ${error.message}`);
                }
            }
        }
        
        // Export document functions
        async function exportDocument(format) {
            const exportBtn = window.event ? window.event.target.closest('button') : null;
            const originalText = exportBtn ? exportBtn.innerHTML : '';
            
            if (exportBtn) {
                exportBtn.innerHTML = '⏳ Exportiere...';
                exportBtn.disabled = true;
            }
            
            let currentContent = '';
            const editorWrapper = document.getElementById('translatedEditorWrapper');
            if (editorWrapper && editorWrapper.style.display === 'block' && typeof tinymce !== 'undefined' && tinymce.get('richTextEditor')) {
                const bodyHtml = tinymce.get('richTextEditor').getContent();
                currentContent = restoreFullHtml(bodyHtml, 'translated');
            } else {
                const iframe = document.getElementById('translatedPreview');
                currentContent = iframe.srcdoc || (iframe.contentDocument ? iframe.contentDocument.documentElement.outerHTML : '');
            }

            try {
                const response = await fetch('/api/export', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        format: format,
                        edited_content: currentContent
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
                if (exportBtn) {
                    exportBtn.innerHTML = originalText;
                    exportBtn.disabled = false;
                }
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
        
        let htmlWrappers = {
            original: { head: '', bodyAttrs: '' },
            translated: { head: '', bodyAttrs: '' }
        };

        function extractBodyAndHead(fullHtml, type) {
            const headMatch = fullHtml.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
            const bodyMatch = fullHtml.match(/<body([^>]*)>([\s\S]*?)<\/body>/i);
            
            if (headMatch && bodyMatch) {
                htmlWrappers[type].head = headMatch[1];
                htmlWrappers[type].bodyAttrs = bodyMatch[1];
                return bodyMatch[2];
            }
            
            const parser = new DOMParser();
            const doc = parser.parseFromString(fullHtml, 'text/html');
            htmlWrappers[type].head = doc.head.innerHTML;
            
            let bodyAttrs = '';
            for (let i = 0; i < doc.body.attributes.length; i++) {
                const attr = doc.body.attributes[i];
                bodyAttrs += ` ${attr.name}="${attr.value}"`;
            }
            htmlWrappers[type].bodyAttrs = bodyAttrs;
            
            return doc.body.innerHTML;
        }

        function restoreFullHtml(bodyHtml, type) {
            return `<!DOCTYPE html>\n<html>\n<head>\n${htmlWrappers[type].head}\n</head>\n<body${htmlWrappers[type].bodyAttrs}>\n${bodyHtml}\n</body>\n</html>`;
        }

        function toggleEditor(show) {
            const translatedIframe = document.getElementById('translatedPreview');
            const originalIframe = document.getElementById('originalPreview');
            const translatedWrapper = document.getElementById('translatedEditorWrapper');
            const originalWrapper = document.getElementById('originalEditorWrapper');
            const editBtn = document.getElementById('editBtn');
            
            if (typeof show !== 'boolean') {
                show = translatedWrapper.style.display === 'none' || translatedWrapper.style.display === '';
            }

            if (show) {
                let originalHtml = originalIframe.srcdoc;
                if (!originalHtml && originalIframe.contentDocument) {
                    originalHtml = originalIframe.contentDocument.documentElement.outerHTML;
                }
                
                let translatedHtml = translatedIframe.srcdoc;
                if (!translatedHtml && translatedIframe.contentDocument) {
                    translatedHtml = translatedIframe.contentDocument.documentElement.outerHTML;
                }
                
                const originalBody = extractBodyAndHead(originalHtml, 'original');
                const translatedBody = extractBodyAndHead(translatedHtml, 'translated');
                
                document.getElementById('originalEditor').value = originalBody;
                document.getElementById('richTextEditor').value = translatedBody;
                
                // Show editors, hide iframes
                translatedIframe.style.display = 'none';
                originalIframe.style.display = 'none';
                translatedWrapper.style.display = 'block';
                originalWrapper.style.display = 'block';
                
                const commonCss = htmlWrappers.translated.head.replace(/<[^>]+>/g, function(match) {
                    return match.toLowerCase().startsWith('<style') || match.toLowerCase().startsWith('</style') ? match : '';
                });
                
                tinymce.init({
                    selector: '#originalEditor, #richTextEditor',
                    height: '100%',
                    width: '100%',
                    promotion: false,
                    branding: false,
                    menubar: 'edit view insert format table',
                    plugins: 'preview searchreplace autolink directionality code visualblocks visualchars fullscreen image link table charmap pagebreak nonbreaking lists wordcount',
                    toolbar: 'undo redo | sds_symbols | styles fontfamily fontsize | bold italic underline subscript superscript | alignleft aligncenter alignright alignjustify | outdent indent | numlist bullist | forecolor backcolor removeformat | table image charmap pagebreak | code fullscreen',
                    style_formats: [
                        { title: 'SDS Formate', items: [
                            { title: 'Abschnitt (z.B. 1.)', block: 'div', classes: 'section-title' },
                            { title: '1.1 Überschrift', block: 'div', classes: 'subsection-title' },
                            { title: '1.1.1 Überschrift', block: 'div', classes: 'subsubsection' },
                            { title: 'Sub-Überschrift (Fett)', inline: 'span', classes: 'sub-heading' },
                            { title: 'Normaler Text', block: 'p' }
                        ]},
                        { title: 'Tabellen Text', items: [
                            { title: 'Text Tabellen', inline: 'span', styles: { fontWeight: 'normal' } },
                            { title: 'Text Tabellen Überschrift', inline: 'span', styles: { fontWeight: 'bold' } }
                        ]}
                    ],
                    table_default_attributes: {
                        class: 'sds'
                    },
                    table_default_styles: {
                        width: '100%',
                        borderCollapse: 'collapse'
                    },
                    table_header_type: 'section',
                    content_style: commonCss + ' body { font-family: Arial, sans-serif; padding: 20px; margin: 0; background: #fff; color: #000 !important; caret-color: #000 !important; } ' +
                                   'table.sds th, table.sds td { border: 1px solid #000; padding: 3px 5px; font-family: Arial, sans-serif; font-size: 9pt; } ' +
                                   'table.sds th { background-color: #F2F2F2; font-weight: bold; text-align: left; }',
                    setup: function (editor) {
                        editor.ui.registry.addButton('sds_symbols', {
                            text: '🛑 Piktogramme',
                            tooltip: 'GHS, PSA & Transport Symbole einfügen',
                            onAction: function () {
                                openSymbolInsertModal(editor);
                            }
                        });
                        editor.on('Change', function () {
                            isDirty = true;
                        });
                        editor.on('Scroll', function() {
                            if (typeof syncAllScrolls !== 'undefined') {
                                syncAllScrolls(editor.id, editor.getWin().scrollY);
                            }
                        });
                    }
                });
                
                // Update button UI (Active state)
                editBtn.innerHTML = '<span class="w-2 h-2 rounded-full bg-white animate-pulse"></span> Editor: Aktiv';
                editBtn.classList.add('bg-minerva-green', 'text-white');
                editBtn.classList.remove('text-minerva-green');
                
                startAutoSave();
            } else {
                if (typeof tinymce !== 'undefined' && tinymce.get('richTextEditor')) {
                    const translatedBody = tinymce.get('richTextEditor').getContent();
                    const originalBody = tinymce.get('originalEditor').getContent();
                    
                    const finalTranslated = restoreFullHtml(translatedBody, 'translated');
                    const finalOriginal = restoreFullHtml(originalBody, 'original');
                    
                    translatedIframe.srcdoc = finalTranslated;
                    originalIframe.srcdoc = finalOriginal;
                    
                    translatedContent = finalTranslated;
                    
                    tinymce.remove('#originalEditor, #richTextEditor');
                }
                
                // Show iframes, hide editors
                translatedIframe.style.display = 'block';
                originalIframe.style.display = 'block';
                translatedWrapper.style.display = 'none';
                originalWrapper.style.display = 'none';
                
                // Update button UI (Inactive state)
                editBtn.innerHTML = '<span class="w-2 h-2 rounded-full bg-minerva-green"></span> Editor: Aus';
                editBtn.classList.remove('bg-minerva-green', 'text-white');
                editBtn.classList.add('text-minerva-green');
                
                stopAutoSave();
            }
        }

        // ======================================================
        // SYMBOL INSERT MODAL LOGIC (TinyMCE)
        // ======================================================
        let activeTinyMCEEditor = null;
        let loadedSymbols = null;

        async function openSymbolInsertModal(editor) {
            activeTinyMCEEditor = editor;
            document.getElementById('symbolInsertModal').classList.add('active');
            
            if (!loadedSymbols) {
                try {
                    const res = await fetch('/api/symbols/list');
                    loadedSymbols = await res.json();
                    renderInsertSymbols();
                } catch (e) {
                    console.error('Failed to load symbols', e);
                }
            }
        }

        function closeSymbolInsertModal() {
            document.getElementById('symbolInsertModal').classList.remove('active');
            activeTinyMCEEditor = null;
        }

        function switchSymbolTab(tab) {
            ['ghs', 'psa', 'transport'].forEach(t => {
                const btn = document.getElementById(`tab-btn-${t}`);
                const content = document.getElementById(`tab-content-${t}`);
                if (t === tab) {
                    btn.classList.add('text-minerva-green', 'border-b-2', 'border-minerva-green');
                    btn.classList.remove('text-light-text-secondary', 'dark:text-minerva-gray');
                    content.classList.remove('hidden');
                } else {
                    btn.classList.remove('text-minerva-green', 'border-b-2', 'border-minerva-green');
                    btn.classList.add('text-light-text-secondary', 'dark:text-minerva-gray');
                    content.classList.add('hidden');
                }
            });
        }

        function renderInsertSymbols() {
            const renderGrid = (containerId, items) => {
                const container = document.getElementById(containerId);
                container.innerHTML = '';
                items.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'bg-white border border-light-border dark:border-minerva-border rounded p-2 text-center cursor-pointer hover:border-minerva-green hover:shadow-lg transition-all transform hover:-translate-y-1';
                    div.onclick = () => insertSymbolToEditor(item.b64, item.name);
                    div.innerHTML = `
                        <img src="${item.b64}" alt="${item.name}" class="w-12 h-12 md:w-16 md:h-16 object-contain mx-auto mb-2">
                        <div class="text-[9px] font-bold text-gray-700 leading-tight break-words mt-1">${item.name}</div>
                    `;
                    container.appendChild(div);
                });
            };

            if (loadedSymbols.ghs) renderGrid('tab-content-ghs', loadedSymbols.ghs);
            if (loadedSymbols.psa) renderGrid('tab-content-psa', loadedSymbols.psa);
            if (loadedSymbols.transport) renderGrid('tab-content-transport', loadedSymbols.transport);
        }

        function insertSymbolToEditor(b64, name) {
            if (activeTinyMCEEditor) {
                // Insert with a specific width so it fits perfectly into the tables
                activeTinyMCEEditor.insertContent(`<img src="${b64}" alt="${name}" style="width: 50px; height: auto; margin: 4px; display: inline-block; vertical-align: middle;" />&nbsp;`);
                closeSymbolInsertModal();
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
            let content = '';
            const translatedWrapper = document.getElementById('translatedEditorWrapper');
            if (translatedWrapper && translatedWrapper.style.display === 'block' && typeof tinymce !== 'undefined' && tinymce.get('richTextEditor')) {
                const bodyHtml = tinymce.get('richTextEditor').getContent();
                content = restoreFullHtml(bodyHtml, 'translated');
            } else {
                const iframe = document.getElementById('translatedPreview');
                content = iframe.srcdoc || (iframe.contentDocument ? iframe.contentDocument.documentElement.outerHTML : '');
            }
            
            if (!content) return;
            
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
        function showSaveStatus(message) {
            const statusIndicator = document.getElementById('save-status-indicator');
            statusIndicator.textContent = message;
            statusIndicator.classList.add('visible');
            setTimeout(() => {
                statusIndicator.classList.remove('visible');
            }, 3000);
        }

        // ======================================================
        // LIBRARY MANAGEMENT LOGIC
        // ======================================================
        // Global deklariert um Doppeldefinition Fehler zu vermeiden
        window.currentLibraryFiles = window.currentLibraryFiles || [];
        
        async function loadLibrary() {
            try {
                const response = await fetch('/api/library/list');
                const data = await response.json();
                
                const tbody = document.getElementById('libraryTableBody');
                if (!tbody) return;
                
                if (data.error) {
                    tbody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-red-500">${data.error}</td></tr>`;
                    return;
                }
                
                currentLibraryFiles = data.files || [];
                renderLibraryTable(currentLibraryFiles);
                
            } catch (error) {
                console.error("Failed to load library:", error);
            }
        }

        function filterLibrary() {
            const query = document.getElementById('librarySearchInput')?.value.toLowerCase() || '';
            const filtered = currentLibraryFiles.filter(f => 
                (f.product && f.product.toLowerCase().includes(query)) ||
                (f.article && f.article.toLowerCase().includes(query)) ||
                (f.filename && f.filename.toLowerCase().includes(query))
            );
            renderLibraryTable(filtered);
        }

        function renderLibraryTable(files) {
            const tbody = document.getElementById('libraryTableBody');
            if (!tbody) return;
            
            if (files.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center p-4 text-light-text-secondary dark:text-minerva-gray">Keine Dokumente gefunden</td></tr>';
                return;
            }
            
            tbody.innerHTML = files.map(file => {
                const safeId = escapeHtml(file.id).replace(/\\/g, '\\\\');
                return `
                <tr class="border-b border-light-border dark:border-minerva-border hover:bg-light-bg dark:hover:bg-[#111111] transition-colors">
                    <td class="p-3 text-light-text dark:text-gray-300 font-medium">
                        ${escapeHtml(file.product || 'Unbekannt')}
                        ${file.article ? `<br><span class="text-[10px] text-minerva-gray">Art: ${escapeHtml(file.article)}</span>` : ''}
                    </td>
                    <td class="p-3 text-light-text-secondary dark:text-minerva-gray">${escapeHtml(file.version || '-')}</td>
                    <td class="p-3 text-light-text-secondary dark:text-minerva-gray">
                        ${escapeHtml(file.language || 'en').toUpperCase()}
                        ${file.country ? ` / ${escapeHtml(file.country)}` : ''}
                    </td>
                    <td class="p-3 text-light-text-secondary dark:text-minerva-gray text-xs">${escapeHtml(file.source || '')}</td>
                    <td class="p-3 text-right">
                        <div class="flex justify-end gap-2">
                            <button onclick="editFromLibrary('${safeId}')" class="p-1.5 bg-blue-500/10 text-blue-500 hover:bg-blue-500 hover:text-white rounded transition-colors" title="Im Editor öffnen">
                                ✏️ Edit
                            </button>
                            <button onclick="exportFromLibrary('${safeId}', 'json')" class="p-1.5 bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white rounded transition-colors" title="JSON Export">
                                💾 JSON
                            </button>
                            <button onclick="deleteFromLibrary('${safeId}')" class="p-1.5 bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white rounded transition-colors" title="Löschen">
                                🗑️
                            </button>
                        </div>
                    </td>
                </tr>
            `}).join('');
        }

        async function editFromLibrary(filepath) {
            try {
                document.getElementById('uploadStatus').innerHTML = `<div class="text-blue-500 text-xs p-2 bg-blue-500/10 rounded">⏳ Lade Dokument aus der Bibliothek...</div>`;
                
                const response = await fetch(`/api/library/load`, { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filepath: filepath })
                });
                const result = await response.json();
                
                if (response.ok) {
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-green-500 text-xs p-2 bg-green-500/10 rounded">✅ Dokument <strong>${result.filename || 'geladen'}</strong> erfolgreich in den Editor geladen.</div>`;
                    
                    const translateTabBtn = document.querySelector('nav button[onclick*="translate"]');
                    if (translateTabBtn) showTab('translate', translateTabBtn);
                    
                    currentFile = result.filename;
                    document.getElementById('originalPreview').srcdoc = result.preview;
                    document.getElementById('previewContainer').style.display = 'flex';
                    document.getElementById('translateBtn').disabled = false;
                    document.getElementById('translatedPreview').srcdoc = '';
                    
                    toggleEditor(false);
                } else {
                    alert(`Fehler beim Laden: ${result.error}`);
                    document.getElementById('uploadStatus').innerHTML = `<div class="text-red-500 text-xs p-2 bg-red-500/10 rounded">❌ Fehler: ${result.error}</div>`;
                }
            } catch (error) {
                alert(`Netzwerkfehler: ${error.message}`);
            }
        }

        async function deleteFromLibrary(filepath) {
            if (!confirm("Möchten Sie dieses Dokument wirklich aus der Bibliothek löschen?")) return;
            try {
                const response = await fetch(`/api/library/delete`, { 
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ filepath: filepath })
                });
                if (response.ok) {
                    loadLibrary(); 
                } else {
                    const result = await response.json();
                    alert(`Fehler beim Löschen: ${result.error}`);
                }
            } catch (error) {
                alert(`Netzwerkfehler: ${error.message}`);
            }
        }
        
        function exportFromLibrary(filepath, format) {
            window.location.href = `/api/library/export?filepath=${encodeURIComponent(filepath)}&format=${format}`;
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
                <tr class="border-b border-light-border dark:border-minerva-border hover:bg-light-bg dark:hover:bg-[#111111] transition-colors">
                    <td class="p-3 text-light-text dark:text-gray-300 w-2/5">
                        <div class="flex items-center gap-2">
                            <span class="text-orange-500 opacity-60">📄</span>
                            <input type="text" value="${escapeHtml(m.sourceField)}" 
                                onchange="updateMapping(${mappingsData.indexOf(m)}, 'sourceField', this.value)"
                                class="bg-white dark:bg-[#0A0A0A] border border-light-border dark:border-minerva-border rounded px-2 py-1.5 text-xs w-full font-mono focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition-all"
                                title="XML-Pfad">
                        </div>
                    </td>
                    <td class="p-3 w-1/4">
                        <span class="inline-block bg-minerva-green/10 text-minerva-green border border-minerva-green/20 rounded px-2 py-1 font-mono text-[11px]">{{ ${escapeHtml(m.templateVar)} }}</span>
                    </td>
                    <td class="p-3 text-light-text-secondary dark:text-minerva-gray text-[11px] italic">${escapeHtml(m.example || '---')}</td>
                    <td class="p-3 text-center">
                        <span class="px-2 py-1 rounded text-[9px] font-bold uppercase tracking-widest ${m.status === 'active' ? 'bg-green-500/10 text-green-500 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}">
                            ${m.status === 'active' ? 'Aktiv' : 'Ignoriert'}
                        </span>
                    </td>
                    <td class="p-3 text-right">
                        <button onclick="toggleMappingStatus(${mappingsData.indexOf(m)})" class="text-[10px] font-bold px-3 py-1.5 rounded border transition-colors ${m.status === 'active' ? 'border-red-500/30 text-red-500 hover:bg-red-500 hover:text-white' : 'border-green-500/30 text-green-500 hover:bg-green-500 hover:text-white'}">
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

        // ✅ GLOBAL FUNKTIONEN FÜR ONCLICK HANDLER VERFÜGBAR MACHEN
        // Alle Funktionen die im HTML mit onclick aufgerufen werden werden hier explizit im globalen Scope registriert
        window.showTab = showTab;
        window.toggleEditor = toggleEditor;
        window.exportDocument = exportDocument;
        window.selectFileType = selectFileType;
        window.handleFileSelect = handleFileSelect;
        window.uploadSingleFile = uploadSingleFile;
        window.uploadCombinedFiles = uploadCombinedFiles;
        window.handleXmlFileSelect = handleXmlFileSelect;
        window.handlePdfFileSelect = handlePdfFileSelect;
        window.translateFile = translateFile;
        window.downloadHTML = downloadHTML;
        window.downloadPDF = downloadPDF;
        window.openGHSModal = openGHSModal;
        window.closeGHSModal = closeGHSModal;
        window.toggleGHSSelection = toggleGHSSelection;
        window.handleDatabaseChange = handleDatabaseChange;
        window.searchPhrases = searchPhrases;
        window.toggleEditorMode = toggleEditorMode;
        window.openLibraryModal = openLibraryModal;
        window.closeLibraryModal = closeLibraryModal;
        window.loadLibraryFiles = loadLibraryFiles;
        window.importFromLibraryByIndex = importFromLibraryByIndex;
