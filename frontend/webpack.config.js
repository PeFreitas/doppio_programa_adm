const path = require('path');

module.exports = {
  // Define o modo para 'development' para evitar o aviso (WARNING)
  mode: 'development',

  // Ponto de entrada: Diz ao Webpack para começar pelo seu arquivo app.ts
  entry: './src/app.ts',

  module: {
    rules: [
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.ts', '.js'],
  },
  // Saída: Diz ao Webpack para salvar o resultado como 'bundle.js' na pasta 'dist'
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
  },
  devtool: 'source-map',
};