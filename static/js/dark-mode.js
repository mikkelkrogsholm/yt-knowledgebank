/**
 * Dark Mode Toggle with Persistence
 * 
 * Handles dark mode state management with localStorage persistence
 * and system preference detection
 */

class DarkModeManager {
    constructor() {
        this.storageKey = 'knowledge-bank-dark-mode';
        this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        this.callbacks = new Set();
        
        this.init();
    }
    
    init() {
        // Get initial theme
        const savedTheme = this.getSavedTheme();
        const systemTheme = this.getSystemTheme();
        
        // Set initial theme (priority: saved > system > light)
        if (savedTheme) {
            this.setTheme(savedTheme);
        } else if (systemTheme) {
            this.setTheme(systemTheme);
        } else {
            this.setTheme('light');
        }
        
        // Listen for system theme changes
        this.mediaQuery.addEventListener('change', (e) => {
            // Only respond to system changes if no manual preference is saved
            if (!this.getSavedTheme()) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });
        
        // Emit initial state
        this.notifyCallbacks();
    }
    
    getSavedTheme() {
        try {
            return localStorage.getItem(this.storageKey);
        } catch (e) {
            console.warn('localStorage not available for dark mode persistence');
            return null;
        }
    }
    
    getSystemTheme() {
        return this.mediaQuery.matches ? 'dark' : 'light';
    }
    
    getCurrentTheme() {
        return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
    }
    
    setTheme(theme) {
        const isDark = theme === 'dark';
        
        // Update DOM
        if (isDark) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        
        // Save preference
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch (e) {
            console.warn('Could not save dark mode preference to localStorage');
        }
        
        // Update meta theme-color for mobile browsers
        this.updateMetaThemeColor(theme);
        
        // Notify callbacks
        this.notifyCallbacks();
        
        // Emit global event
        if (typeof eventSystem !== 'undefined') {
            eventSystem.emit('themeChanged', { theme, isDark });
        }
    }
    
    toggle() {
        const currentTheme = this.getCurrentTheme();
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
        return newTheme;
    }
    
    isDark() {
        return this.getCurrentTheme() === 'dark';
    }
    
    isLight() {
        return this.getCurrentTheme() === 'light';
    }
    
    followSystem() {
        // Remove saved preference to follow system
        try {
            localStorage.removeItem(this.storageKey);
        } catch (e) {
            console.warn('Could not remove dark mode preference from localStorage');
        }
        
        // Set to current system preference
        this.setTheme(this.getSystemTheme());
    }
    
    updateMetaThemeColor(theme) {
        let metaThemeColor = document.querySelector('meta[name="theme-color"]');
        
        if (!metaThemeColor) {
            metaThemeColor = document.createElement('meta');
            metaThemeColor.name = 'theme-color';
            document.head.appendChild(metaThemeColor);
        }
        
        const color = theme === 'dark' ? '#1f2937' : '#ffffff';
        metaThemeColor.content = color;
    }
    
    onChange(callback) {
        this.callbacks.add(callback);
        
        // Return unsubscribe function
        return () => {
            this.callbacks.delete(callback);
        };
    }
    
    notifyCallbacks() {
        const theme = this.getCurrentTheme();
        const isDark = theme === 'dark';
        
        this.callbacks.forEach(callback => {
            try {
                callback({ theme, isDark });
            } catch (error) {
                console.error('Dark mode callback error:', error);
            }
        });
    }
    
    getPreference() {
        const saved = this.getSavedTheme();
        const system = this.getSystemTheme();
        const current = this.getCurrentTheme();
        
        return {
            saved,
            system,
            current,
            followingSystem: !saved
        };
    }
}

// Alpine.js Dark Mode Component
function darkModeToggle() {
    return {
        isDark: false,
        isFollowingSystem: false,
        systemPreference: 'light',
        darkModeManager: null,
        
        init() {
            this.darkModeManager = new DarkModeManager();
            
            // Set initial state
            this.updateState();
            
            // Listen for changes
            this.darkModeManager.onChange(() => {
                this.updateState();
            });
        },
        
        updateState() {
            const preference = this.darkModeManager.getPreference();
            this.isDark = preference.current === 'dark';
            this.isFollowingSystem = preference.followingSystem;
            this.systemPreference = preference.system;
        },
        
        toggle() {
            const newTheme = this.darkModeManager.toggle();
            
            // Show notification
            if (typeof eventSystem !== 'undefined') {
                eventSystem.notify(
                    `Switched to ${newTheme} mode`,
                    'info',
                    2000
                );
            }
        },
        
        setLight() {
            this.darkModeManager.setTheme('light');
        },
        
        setDark() {
            this.darkModeManager.setTheme('dark');
        },
        
        followSystem() {
            this.darkModeManager.followSystem();
            
            if (typeof eventSystem !== 'undefined') {
                eventSystem.notify(
                    'Now following system preference',
                    'info',
                    2000
                );
            }
        },
        
        getToggleIcon() {
            return this.isDark ? '☀️' : '🌙';
        },
        
        getToggleText() {
            return this.isDark ? 'Light mode' : 'Dark mode';
        },
        
        getSystemIndicator() {
            if (!this.isFollowingSystem) return '';
            return ` (Following system: ${this.systemPreference})`;
        }
    };
}

// Initialize dark mode immediately (before Alpine.js)
const globalDarkMode = new DarkModeManager();

// Export for both browser and Node.js environments
if (typeof window !== 'undefined') {
    window.DarkModeManager = DarkModeManager;
    window.darkModeToggle = darkModeToggle;
    window.globalDarkMode = globalDarkMode;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { DarkModeManager, darkModeToggle };
}