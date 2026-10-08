#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QString>
#include <QJsonArray>

class ApiClient : public QObject
{
    Q_OBJECT

public:
    explicit ApiClient(QObject *parent = nullptr);

    void uploadImage(const QString &filePath);

    void startAnalysis(qint64 imageId);
    void getAnalysisStatus(qint64 requestId);

signals:
    void imageUploaded(qint64 imageId);
    void uploadFailed(const QString &errorMessage);

    void analysisStarted(qint64 requestId, const QString &status);
    void analysisStartFailed(const QString &errorMessage);

    void analysisStatusReceived(
        qint64 requestId,
        const QString &status,
        const QJsonArray &detections,
        const QString &errorCode,
        const QString &errorMessage
        );

    void analysisStatusFailed(const QString &errorMessage);

private:
    QNetworkAccessManager *networkManager;

    QString baseUrl = "https://gumming-unmasking-unhitched.ngrok-free.dev";
};

#endif // APICLIENT_H
