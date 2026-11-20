import 'package:flutter/material.dart';
import 'package:water_revenue_predictor/models/prediction_result.dart';

class ResultScreen extends StatelessWidget {
  final PredictionResult predictionResult;

  const ResultScreen({super.key, required this.predictionResult});

  @override
  Widget build(BuildContext context) {
    final revenue = predictionResult.predictedAnnualRevenue;
    final currency = predictionResult.currency;

    return Scaffold(
      appBar: AppBar(title: const Text('Prediction Result')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 32),
              Icon(
                Icons.water_drop_outlined,
                size: 72,
                color: Theme.of(context).colorScheme.primary,
              ),

              const SizedBox(height: 24),

              Text(
                'Estimated Annual Revenue',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleLarge,
              ),

              const SizedBox(height: 16),

              Text(
                '\$${revenue.toStringAsFixed(2)}',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.displayMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),

              const SizedBox(height: 8),

              Text(
                '$currency per year',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleMedium,
              ),

              const SizedBox(height: 32),

              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(
                    'This estimate is generated using a trained '
                    'Random Forest model based on rural water '
                    'infrastructure characteristics. Actual '
                    'revenue may differ.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),

              const Spacer(),
              FilledButton.icon(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.refresh),
                label: const Text('Make Another Prediction'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
