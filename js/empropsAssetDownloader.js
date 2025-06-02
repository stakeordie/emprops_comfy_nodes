// Added: 2025-05-12T13:52:12-04:00 - Asset Downloader implementation
// Updated: 2025-05-12T14:08:00-04:00 - Added support for output signals
// Updated: 2025-06-02T11:43:17-04:00 - Added token provider support
import { app } from "../../scripts/app.js"
import { api } from "../../scripts/api.js"

// Token providers configuration
const TOKEN_PROVIDERS = {
    'None': { showTokenInput: false },
    'Hugging Face': { showTokenInput: false },
    'Custom': { showTokenInput: true }
};

app.registerExtension({
    name: "EmProps Asset Downloader",
    async setup() {        
        // [2025-05-30T10:38:56-04:00] Updated node names to match ComfyUI structure
        const nodeTypes = [
            "EmProps_Asset_Downloader",
            "EmProps_Checkpoint_Loader",
            "EmProps_VAE_Loader",
            "EmProps_Upscaler_Loader",
            "EmProps_ControlNet_Loader",
            "EmProps_DualCLIP_Loader",
            "EmProps_Diffusion_Model_Loader",
            "EmProps_CLIP_Loader"
        ]
        
        // Handle token provider change
        const onTokenProviderChange = function(event, node, tokenInput) {
            const provider = event.target.value;
            const showTokenInput = TOKEN_PROVIDERS[provider]?.showTokenInput || false;
            
            // Find the token input widget
            const tokenWidget = node.widgets.find(w => w.name === 'token');
            if (tokenWidget) {
                // Store the current token value
                const currentValue = tokenWidget.value;
                
                // Update the widget properties
                tokenWidget.hidden = !showTokenInput;
                
                // Restore the token value
                tokenWidget.value = currentValue;
                
                // Trigger a graph change to update the UI
                node.setSize([node.size[0], node.computeSize()[1]]);
                app.graph.setDirtyCanvas(true, true);
            }
        };
        
        // Add token provider UI handling to the Asset Downloader
        const origNodeCreated = app.registerNodeType("EmProps_Asset_Downloader", function(node) {
            // Find the token provider dropdown
            const tokenProviderWidget = node.widgets.find(w => w.name === 'token_provider');
            const tokenWidget = node.widgets.find(w => w.name === 'token');
            
            if (tokenProviderWidget && tokenWidget) {
                // Initially hide the token input if not needed
                const provider = tokenProviderWidget.value || 'None';
                tokenWidget.hidden = !TOKEN_PROVIDERS[provider]?.showTokenInput;
                
                // Add change handler to the token provider dropdown
                tokenProviderWidget.callback = (event) => onTokenProviderChange(event, node, tokenWidget);
            }
        });
        
        nodeTypes.forEach(nodeType => {
            const origNode = LiteGraph.registered_node_types[nodeType];
            if (!origNode) {
                console.error(`Original node not found: ${nodeType}`);
                return;
            }

            // Store the original onNodeCreated function
            const origOnNodeCreated = origNode.prototype.onNodeCreated;
            
            // Override onNodeCreated to add our custom UI handling
            origNode.prototype.onNodeCreated = function() {
                // Call the original onNodeCreated if it exists
                if (origOnNodeCreated) {
                    origOnNodeCreated.apply(this, arguments);
                }
                
                // Only apply to Asset Downloader
                if (nodeType === "EmProps_Asset_Downloader") {
                    // Find the token provider dropdown
                    const tokenProviderWidget = this.widgets?.find(w => w.name === 'token_provider');
                    const tokenWidget = this.widgets?.find(w => w.name === 'token');
                    
                    if (tokenProviderWidget && tokenWidget) {
                        // Initially hide the token input if not needed
                        const provider = tokenProviderWidget.value || 'None';
                        tokenWidget.hidden = !TOKEN_PROVIDERS[provider]?.showTokenInput;
                        
                        // Add change handler to the token provider dropdown
                        tokenProviderWidget.callback = (event) => onTokenProviderChange(event, this, tokenWidget);
                    }
                }
            };

            // Render progress on title bar
            origNode.prototype.onDrawTitleBar = function(ctx, title_height, size, collapsed) {
                if (this.progress !== undefined) {
                    const progress = Math.min(100, Math.max(0, this.progress));
                    const width = (size[0] * progress) / 100;
                    
                    ctx.save();
                    ctx.fillStyle = "#2080ff44";
                    const radius = 4;
                    ctx.beginPath();
                    ctx.roundRect(0, 0, width, title_height, [radius, radius, 0, 0]);
                    ctx.fill();
                    ctx.restore();
                }

                if (!collapsed) {
                    ctx.fillStyle = "#fff";
                    ctx.font = LiteGraph.NODE_TEXT_SIZE + "px Arial";
                    ctx.textAlign = "left";
                    ctx.fillText(this.title, 4, title_height * 0.7);
                }
            };

            // Add progress handling method
            origNode.prototype.setProgress = function(progress) {
                this.progress = progress;
                this.setDirtyCanvas(true);
            };
        });

        // Register progress event listener
        api.addEventListener("progress", ({ detail }) => {
            if (!detail.node) return;
            
            const node = app.graph.getNodeById(detail.node);
            if (!node || !nodeTypes.includes(node.type)) {
                return;
            }
            
            const progress = (detail.value / detail.max) * 100;
            node.setProgress(progress);
        });
    }
})
