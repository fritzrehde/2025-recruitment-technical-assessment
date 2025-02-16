use axum::{http::StatusCode, response::IntoResponse, Json};
use serde::{Deserialize, Serialize};

pub async fn process_data(Json(request): Json<DataRequest>) -> impl IntoResponse {
    // TODO(done): Calculate sums and return response
    let response = request.process();
    (StatusCode::OK, Json(response))
}

#[derive(Deserialize)]
pub struct DataRequest {
    // TODO(done): Add any fields here
    data: Vec<Data>,
}

impl DataRequest {
    fn process(&self) -> DataResponse {
        let (string_len, int_sum) =
            self.data
                .iter()
                .fold((0, 0), |(string_len_acc, int_sum_acc), data| match data {
                    Data::String(s) => (string_len_acc + s.len(), int_sum_acc),
                    Data::Int(i) => (string_len_acc, int_sum_acc + i),
                });

        DataResponse {
            string_len,
            int_sum,
        }
    }
}

#[derive(Deserialize)]
#[serde(untagged)]
enum Data {
    String(String),
    Int(usize),
}

#[derive(Debug, Serialize, PartialEq, Eq)]
struct DataResponse {
    // TODO(done): Add any fields here
    string_len: usize,
    int_sum: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_data() {
        let request = DataRequest {
            data: vec![
                Data::String("Hello".to_string()),
                Data::Int(1),
                Data::Int(5),
                Data::String("World".to_string()),
                Data::String("!".to_string()),
            ],
        };

        let response = request.process();
        assert_eq!(
            DataResponse {
                string_len: 11,
                int_sum: 6
            },
            response
        );
    }
}
