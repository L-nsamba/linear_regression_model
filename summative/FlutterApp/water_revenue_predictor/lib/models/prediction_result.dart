class PredictionResult {
  final double predictedAnnualRevenue;
  final String currency;

  PredictionResult({
    required this.predictedAnnualRevenue,
    required this.currency,
  });

  factory PredictionResult.fromJson(Map<String, dynamic> json) {
    return PredictionResult(
      predictedAnnualRevenue: (json['predicted_annual_revenue'] as num)
          .toDouble(),
      currency: json['currency'] as String,
    );
  }
}
