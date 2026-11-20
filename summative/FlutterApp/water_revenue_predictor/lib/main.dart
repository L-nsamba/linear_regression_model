import 'package:flutter/material.dart';
import 'package:water_revenue_predictor/screens/prediction_screen.dart';

void main() {
  runApp(const WaterRevenueApp());
}

class WaterRevenueApp extends StatelessWidget {
  const WaterRevenueApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Water Revenue Prediction App',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.teal),
        useMaterial3: true,
      ),
      home: const PredictionScreen(),
    );
  }
}
