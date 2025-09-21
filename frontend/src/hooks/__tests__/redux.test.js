describe('Redux Hooks', () => {
  test('should export useAppDispatch', () => {
    const reduxHooks = require('../redux');
    expect(reduxHooks.useAppDispatch).toBeDefined();
    expect(typeof reduxHooks.useAppDispatch).toBe('function');
  });

  test('should export useAppSelector', () => {
    const reduxHooks = require('../redux');
    expect(reduxHooks.useAppSelector).toBeDefined();
    expect(typeof reduxHooks.useAppSelector).toBe('function');
  });
});
