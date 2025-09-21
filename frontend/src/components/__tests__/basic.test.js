const { render } = require('@testing-library/react');
const React = require('react');

// Basic component test
describe('Basic Component Tests', () => {
  test('should render a simple component', () => {
    const SimpleComponent = () => React.createElement('div', { 'data-testid': 'simple' }, 'Hello World');
    
    const { getByTestId } = render(React.createElement(SimpleComponent));
    
    expect(getByTestId('simple')).toBeInTheDocument();
    expect(getByTestId('simple')).toHaveTextContent('Hello World');
  });

  test('should render with props', () => {
    const PropsComponent = ({ message }) => React.createElement('div', { 'data-testid': 'props' }, message);
    
    const { getByTestId } = render(React.createElement(PropsComponent, { message: 'Test Message' }));
    
    expect(getByTestId('props')).toHaveTextContent('Test Message');
  });
});
