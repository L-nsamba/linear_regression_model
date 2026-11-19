import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:water_revenue_predictor/models/prediction_result.dart';
import 'package:water_revenue_predictor/models/water_point_input.dart';

class PredictionService {
  static final Uri _predictionUrl = Uri.parse(
    'https://water-revenue-prediction-api.onrender.com/predict',
  );

  static const Duration _timeout = Duration(seconds: 60);

  Future<PredictionResult> predictRevenue(WaterPointInput input) async {
    try {
      // Send infrastructure data to FastAPI
      final response = await http
          .post(
            _predictionUrl,
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(input.toJson()),
          )
          .timeout(_timeout);

      // Decode the API response
      final decoded = jsonDecode(response.body);

      if (response.statusCode == 200) {
        if (decoded is! Map<String, dynamic>) {
          throw const FormatException('Unexpected response format.');
        }

        return PredictionResult.fromJson(decoded);
      }

      // Handle API validation errors
      if (response.statusCode == 422) {
        throw PredictionException(
          'Some input values were rejected. Please check the form.',
        );
      }

      if (response.statusCode >= 500) {
        throw PredictionException(
          'The prediction server is temporarily unavailable.',
        );
      }

      throw PredictionException(
        'Prediction failed (HTTP ${response.statusCode}).',
      );
    } on TimeoutException {
      throw PredictionException('The request timed out. Please try again.');
    } on SocketException {
      throw PredictionException(
        'Could not connect to the server. Check your internet connection.',
      );
    } on http.ClientException {
      throw PredictionException('A network error occurred. Please try again.');
    } on FormatException {
      throw PredictionException('The server returned an unexpected response.');
    }
  }
}

class PredictionException implements Exception {
  final String message;

  const PredictionException(this.message);

  @override
  String toString() => message;
}
