describe('Theme Configuration', () => {
  test('should export theme object', () => {
    const theme = require('../theme');
    expect(theme).toBeDefined();
    expect(theme.default).toBeDefined();
  });

  test('should have Material-UI palette configuration', () => {
    const theme = require('../theme');
    const themeConfig = theme.default;
    
    expect(themeConfig).toHaveProperty('palette');
    expect(themeConfig.palette).toHaveProperty('primary');
    expect(themeConfig.palette).toHaveProperty('secondary');
  });

  test('should have typography configuration', () => {
    const theme = require('../theme');
    const themeConfig = theme.default;
    
    expect(themeConfig).toHaveProperty('typography');
  });

  test('should have breakpoints configuration', () => {
    const theme = require('../theme');
    const themeConfig = theme.default;
    
    expect(themeConfig).toHaveProperty('breakpoints');
  });

  test('should have components configuration', () => {
    const theme = require('../theme');
    const themeConfig = theme.default;
    
    expect(themeConfig).toHaveProperty('components');
  });
});
